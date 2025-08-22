import logging

from pydantic import ValidationError

from providers.schemas.wallex_schemas import OrderResponseSchema, OrderResultSchema

logger = logging.getLogger(__name__)


def validate_response_schema(response: dict) -> OrderResponseSchema:
    """
    Validates the provider's response schema to ensure it conforms to the expected structure.

    Args:
        response (dict): The raw response returned from the provider.

    Returns:
        OrderResponseSchema: The validated response schema.

    Raises:
        ValueError: If the response schema is invalid.
        ValidationError: If the response does not match the expected schema.
    """
    logger.info(f"Validating the response schema from provider.")
    print(f" DEBUG: Starting schema validation...")

    if not response:
        logger.warning(f" The response from the provider is empty or None.{response}")
        print(f" ERROR: The response from the provider is empty or None.{response}")
        return OrderResponseSchema(message=None,success=None,result=None)

    try:
        result = response.get('result')
        if result is None:
            logger.error(f" The response result is missing or None.")
            print(f" ERROR: The response result is missing or None.")
            validated_schema = OrderResponseSchema(
                success=response.get('success', ""),
                message=response.get('message', ""),
                result=OrderResultSchema(),
            )
            return validated_schema

        result_schema = OrderResultSchema(
            symbol=result.get('symbol'),
            type=result.get('type'),
            side=result.get('side'),
            price=result.get('price'),
            orig_qty=result.get('origQty'),
            orig_sum=result.get('origSum'),
            executed_price=result.get('executedPrice'),
            executed_qty=result.get('executedQty'),
            executed_sum=result.get('executedSum'),
            executed_percent=result.get('executedPercent'),
            status=result.get('status'),
            active=result.get('active'),
            timestamp_created_at=str(result.get('transactTime')),
            client_order_id=result.get('clientOrderId'),
        )

        logger.info(f"Successfully validated 'result' field with schema.")
        print(f" DEBUG: Validated result schema: {result_schema}")

        validated_schema = OrderResponseSchema(
            success=response.get('success'),
            message=response.get('message', ""),
            result=result_schema,
        )
        logger.info(f" Successfully validated the complete response schema.")
        print(f"DEBUG: Final validated response schema: {validated_schema}")

        return validated_schema

    except ValidationError as e:
        logger.error(f" Schema validation failed: {e}")
        print(f"ERROR: Schema validation failed: {e}")
        raise ValueError("Schema validation failed.") from e
