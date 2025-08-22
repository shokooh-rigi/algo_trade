from logging import getLogger
from celery import signals
import time

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from celery import current_app

from algo.models import Deal, StrategyConfig, Order
from algo.services.cancel_order_service import CancelOrderService
from algo.strategies.enums import ProcessedSideEnum, StrategyState
from algo_trade import settings

logger = getLogger(__name__)

@receiver(post_save, sender=StrategyConfig)
def update_strategy_state(sender, instance, created, **kwargs):
    """
    Signal triggered after saving a StrategyConfig instance.
    Updates the state of the strategy to 'UPDATED' when the instance is updated,
    not when it is created.
    """
    if instance.turn_off_ordering:
        """
        cancel active orders 
        """
        StrategyConfig.update_state(
            id=instance.id,
            state=StrategyState.NOT_ORDERING.value,
        )
        active_orders = Order.objects.filter(
            store_client=instance.store_client,
            strategy_result__strategy_config=instance,
            active=True,
            ).all()
        if active_orders:
            for active_order in active_orders:
                cancel_order_service = CancelOrderService(
                    store_client=instance.store_client,
                    client_order_id=active_order.client_order_id,
                )
                cancel_order_service.cancel_order()
                time.sleep(1) # because of rate limitation in provider
        elif not instance.is_active:
            """
            if strategy is not active, set state to STOPPED
            """
            StrategyConfig.update_state(
                id=instance.id,
                state=StrategyState.STOPPED.value,
            )


    if not created:
        try:
            if not instance.is_active:
                """
                If the strategy is not active and cancel active orders for strategy config
                """
                StrategyConfig.update_state(
                    id=instance.id,
                    state=StrategyState.STOPPED.value,
                )
                active_orders = Order.objects.filter(
                    store_client=instance.store_client,
                    strategy_result__strategy_config=instance,
                    active=True,
                ).all()
                if active_orders:
                    for active_order in active_orders:
                        cancel_order_service = CancelOrderService(
                            store_client=instance.store_client,
                            client_order_id=active_order.client_order_id,
                        )
                        cancel_order_service.cancel_order()
                        time.sleep(1)  # because of rate limitation in provider
                    logger.info(f"Canceled orders for strategy {instance.id} due to inactivity.")

            # Fetch previous state from DB
            old_instance = sender.objects.get(pk=instance.pk)
            fields_to_check = ['sensitivity_percent', 'market', 'strategy_configs']

            changed = any(
                getattr(old_instance, field) != getattr(instance, field)
                for field in fields_to_check
            )

            if changed and not instance.is_deleted and not instance.turn_off_ordering:
                # Cancel active orders if relevant fields changed
                active_orders = Order.objects.filter(
                    store_client=instance.store_client,
                    strategy_result__strategy_config=instance,
                    active=True,
                ).all()
                for active_order in active_orders:
                    cancel_order_service = CancelOrderService(
                        store_client=instance.store_client,
                        client_order_id=active_order.client_order_id,
                    )
                    cancel_order_service.cancel_order()
                    time.sleep(1)
                logger.info(f"Canceled orders for strategy {instance.id} due to config change.")

            if not instance.is_deleted and not instance.turn_off_ordering and instance.is_active:
                StrategyConfig.update_state(id=instance.id, state=StrategyState.UPDATED.value)
                logger.info(f"Updated state of strategy {instance.id} to {StrategyState.UPDATED.value}.")
        except sender.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"Failed to update state for strategy {instance.id}: {str(e)}")
            raise
    else:
        logger.info(f"StrategyConfig with id {instance.id} was created. No state change.")


@receiver(pre_delete, sender=StrategyConfig)
def handle_strategy_config_delete(sender, instance, **kwargs):
    """
    Signal to handle `StrategyConfig` deletions.
        Deletes related `StrategyResult` rows that were unprocessed.
    """
    active_orders = Order.objects.filter(
        strategy_result__strategy_config=instance,
        active=True
    ).all()
    if not active_orders:
        logger.info(f"{settings.LOG_CANCEL_PREFIX} No active orders found for strategy {instance.strategy} "
                    f"on market {instance.market.symbol}."
                    )
        return f"No active orders found for strategy {instance.strategy} on market {instance.market.symbol}."
    for active_order in active_orders:
        cancel_order_service = CancelOrderService(
            store_client=active_order.store_client,
            client_order_id=active_order.client_order_id,
        )
        cancel_order_service.cancel_order()
        time.sleep(1)  # because of rate limitation in provider

    # Delete only unprocessed StrategyResult rows
    deleted_count, _ = Deal.objects.filter(
        strategy_config=instance,
        processed=False,
        processed_side=ProcessedSideEnum.NONE.value,
    ).delete()
    logger.info(
        f"{deleted_count} unprocessed StrategyResult rows related to StrategyConfig {instance.id} were deleted."
    )

