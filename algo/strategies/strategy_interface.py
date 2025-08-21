from abc import ABC, abstractmethod

class StrategyInterface(ABC):
    @abstractmethod
    def initialize(self, price_history):
        """Initialize strategy parameters."""
        pass

    @abstractmethod
    def execute(self, data):
        """Execute strategy logic on the given data."""
        pass

    @abstractmethod
    def get_results(self):
        """Return the results of the strategy execution."""
        pass
