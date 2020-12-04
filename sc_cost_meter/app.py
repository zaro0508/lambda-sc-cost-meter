import json
import logging
import sc_cost_meter.utils as utils

from datetime import datetime, timedelta

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def get_time_period_yesterday():
  current_time = datetime.utcnow()
  start_time = current_time - timedelta(days=2)
  end_time = current_time - timedelta(days=1)
  time_period = {
    "Start": start_time.strftime('%Y-%m-%d'),
    "End": end_time.strftime('%Y-%m-%d')
  }

  return time_period

def lambda_handler(event, context):
  synapse_ids = utils.get_marketplace_synapse_ids()
  log.debug(f'customers list: {synapse_ids}')
  failures = 0
  success = 0
  for synapse_id in synapse_ids:
    customer_info = utils.get_marketplace_customer_info(synapse_id)
    log.debug(f'marketplace customer info: {customer_info}')
    if len(customer_info) == 0:
      continue

    customer_id = customer_info['MarketplaceCustomerId']
    product_code = customer_info['ProductCode']
    yesterday = get_time_period_yesterday()
    cost, unit = utils.get_customer_cost(customer_id, yesterday, "DAILY")
    status, result = utils.report_cost(cost, customer_id, product_code)
    if status == 'Failed':
      failures = failures + 1
      log.info(f'Failed to report cost for product {product_code} to customer {customer_id}')
    else:
      record_id = result['MeteringRecordId']
      log.info(f'Successfully reported cost for product {product_code}'
                f'to customer {customer_id} with record id {record_id}')
      success = success + 1

  message = f'Metering processed: failed reports ({failures}), successful reports ({success})'
  log.info(message)
  response = {
    "statusCode": 200,
    "body": json.dumps({
      "message": message,
    }),
  }
  return response
