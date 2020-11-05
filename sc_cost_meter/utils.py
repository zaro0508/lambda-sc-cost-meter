import awspricing
import boto3
import logging
import os

from datetime import datetime

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

os.environ["AWSPRICING_USE_CACHE"] = "1"  # enable cache for awspricing

def get_ec2_client():
  return boto3.client('ec2')

def get_ssm_client():
  return boto3.client('ssm')

def get_meteringmarketplace_client():
  return boto3.client('meteringmarketplace')

def get_instances(states):
   client = get_ec2_client()
   response = client.describe_instances(
      Filters=[
         {
            'Name': 'instance-state-name',
            'Values': states
         }
      ]
   )

   instances = []
   reservations = response["Reservations"]
   if reservations:
      for reservation in reservations:
          for instance in reservation["Instances"]:
            instances.append(instance)

   return instances

def get_ec2_on_demand_pricing(instance):
  instance_region = instance['Placement']['AvailabilityZone'][0:-1]
  instance_id = instance['InstanceId']
  instance_type = instance['InstanceType']

  client = get_ssm_client()
  response = client.describe_instance_information(
    Filters=[
       {
          'Key': 'InstanceIds',
          'Values': [instance_id]
       }
    ]
  )
  ssm_instance_info = response['InstanceInformationList'][0]
  instance_platform = ssm_instance_info['PlatformType']

  ec2_offer = awspricing.offer('AmazonEC2')
  price = ec2_offer.ondemand_hourly(
    instance_type,
    operating_system=instance_platform,
    region=instance_region
  )

  log.debug(f'price for {instance_id} is {price}')
  return price

def get_tags(instance):
  client = get_ec2_client()
  response = client.describe_tags(
    Filters = [
       {
          'Name': 'resource-id',
          'Values': [
             instance,
          ]
       }
    ]
  )
  tags = response['Tags']
  log.debug(f'instance tags = {tags}')
  return tags


def get_marketplace_product_code(instance):
   product_codes = instance['ProductCodes']
   if len(product_codes) >= 1:
      for product_code in product_codes:
         if product_code['ProductCodeType'] == 'marketplace':
           product_code_id = product_code['ProductCodeId']
           log.debug(f'Product Code ID = {product_code_id}')
           return product_code_id

   return None


def report_usage(price, customer_id, product_code):
  cost_accrued_rate = 0.0001  # TODO: use mareketplace get_dimension API to get this info
  quantity = int(price / cost_accrued_rate)

  mrktpl_client = get_meteringmarketplace_client()
  mrktpl_client.batch_meter_usage(
    UsageRecords=[
      {
        'Timestamp': datetime.now(),
        'CustomerIdentifier': customer_id,
        'Dimension': 'costs_accrued',
        'Quantity': quantity
      }
    ],
    ProductCode=product_code
  )