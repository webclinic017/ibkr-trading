import logging
from datetime import date
from ib_async import IB

from models import OptionSpreads

logger = logging.getLogger(__name__)


def need_to_open_spread(ibkr: IB, spreads: list[OptionSpreads]):
  """
  Check trade logic
  TODO: add the logic here
  TODO: check for delta of the short leg
  TODO: check for symbols - we assume it is only SPXW
  """
  # When empty, we need to open a spread
  return_flag = True

  if len(spreads) == 2:
    return_flag = False
  if len(spreads) == 1:
    # Check if the existing spread expires today
    today = date.today().strftime("%Y%m%d")
    if spreads[0].expiry == today:
      # Get contract details and modelGreeks for the short leg
      short_contract = [
        leg for leg in spreads[0].legs if leg.strike == spreads[0].strike
      ][0]
      ibkr.reqMktData(short_contract.conId, "ModelGreeks", False, False)

      # Update delta from live market data
      current_delta = short_contract.modelGreeks.delta

      if current_delta > -0.02:
        return_flag = True
      else:
        return_flag = False
    else:
      return_flag = False

  return return_flag


def target_delta() -> float:
  """
  Target delta
  TODO: add the logic here

  """
  return -0.06


def target_protection() -> float:
  """
  Target protection
  TODO: add the logic here
  """
  return 100


def position_size(ibkr: IB) -> int:
  """
  Position size
  TODO: add the logic here
  """
  net_value = float(
    [
      v
      for v in ibkr.accountValues()
      if v.tag == "NetLiquidationByCurrency" and v.currency == "BASE"
    ][0].value
  )
  position_size = round(net_value * 0.25 / target_protection() / 100)
  return position_size


if __name__ == "__main__":
  ibkr = IB()
  ibkr.connect("localhost", 8888)
  position_size = position_size(ibkr)
  print("Position size: ", position_size)
  ibkr.disconnect()
