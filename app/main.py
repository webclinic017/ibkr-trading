"""
Gateway - interactions with TWS API
"""

import datetime as dt
import logging
import schedule
import time

from ib_async import IB

from settings import Settings
from trade_logic import need_to_open_spread, get_spread_to_open

from services.positions import PositionsService
from messaging.ntfy import MessageHandler
from mocks.ib_mock import MockIB

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  datefmt="%Y-%m-%d %H:%M:%S",
  handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)
logging.getLogger("ib_async").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class ConnectionIssue(Exception):
  """My custom exception class."""


class TradingBot:
  """
  Trading bot class, which orchestrates interactions with the IB API
  and trade logic
  """

  def __init__(self, settings, mock_data_path=None):
    self.config = settings
    self.ibkr = None
    self.spreads = None
    self.positions = None
    self.net_value = None
    self._connect(mock_data_path)

  def __del__(self):
    try:
      self.ibkr.disconnect()
    except AttributeError:
      pass

  def _connect(self, mock_data_path=None):
    """
    Create and connect IB client
    """
    host = self.config.ib_gateway_host
    port = self.config.ib_gateway_port

    if mock_data_path:
      self.ibkr = MockIB(mock_data_path)
    else:
      self.ibkr = IB()

    try:
      self.ibkr.connect(
        host=host,
        port=port,
        clientId=dt.datetime.now(dt.UTC).strftime("%H%M"),
        timeout=120,
        readonly=True,
      )
      self.ibkr.RequestTimeout = 30
    except ConnectionIssue as e:
      logger.error("Error connecting to IB: %s", e)
    logger.debug("Connected to IB on %s:%s", host, port)

    try:
      self.positions = self.ibkr.positions()
    except Exception as e:
      logger.error("Error getting positions: %s", e)
      raise e

  def trade_loop(self):
    """
    Main trading loop
    """

    # Create telegram status bot
    status_bot = MessageHandler(self.config)

    # Get existing option spreads
    positions_service = PositionsService(self.ibkr, self.positions)
    existing_spreads = positions_service.get_option_spreads()
    self.spreads = existing_spreads
    for spread in self.spreads:
      logger.info("Found spread: %s", spread)
    status_bot.send_positions(existing_spreads)

    # Identify if spreads need to be opened
    if not need_to_open_spread(self.ibkr, existing_spreads):
      logger.info("No spreads need to be opened")
      status_bot.send_notification("No spreads need to be opened")
      return

    # Close the spread with execution logic
    if self.config.close_spread_on_expiry:
      # TODO: implement the closing logic
      pass

    # Identify which spreads needs to be opened
    contract = get_spread_to_open(self.ibkr, existing_spreads)
    logger.info("Target spread: %s", contract)
    status_bot.send_target_spread(contract)

    # # Open the spread with execution logic
    # spread_service = OptionSpreadService(self.ibkr, contract)
    # current_price = spread_service.get_current_price()
    # logger.info("Current price of the target spread: %s", current_price)
    # spread_service.trade_spread()


if __name__ == "__main__":
  # Create trading bot
  settings = Settings()
  bot = TradingBot(settings, mock_data_path="./data/positions.pickle")

  schedule.every(60).minutes.do(bot.trade_loop)
  schedule.run_all()
  logger.info("Started schedule")
  while True:
    schedule.run_pending()
    time.sleep(1)
