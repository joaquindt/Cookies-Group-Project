import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import PriorityQueue
import time
import random
from queue import Empty
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import os
import base64
from email import message_from_bytes


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Order:
    def __init__(self, order_id, cookie_type, quantity, priority=100):
        self.order_id = order_id
        self.cookie_type = cookie_type
        self.quantity = quantity
        self.priority = priority
        self.status = 'Pending'
        self.processing_time = None
        self.processing_time = None  # Overall time to process the order
        # Production steps time (in seconds for simulation)
        self.wash_and_mix_time = 6  # 6 seconds to simulate 6 minutes
        self.spoon_onto_tray_time = 2  # 2 seconds to simulate 2 minutes per tray
        self.bake_time = 10  # 10 seconds to simulate 10 minutes per tray
        self.cool_time = 5  # 5 seconds to simulate 5 minutes
        self.pack_and_payment_time = 3  # 3 seconds to simulate 3 minutes per dozen

    def __lt__(self, other):
        return self.priority < other.priority

    def wash_and_mix(self):
        # Simulate wash and mix time

        time.sleep(self.wash_and_mix_time)
        logging.info(f"Order:{self.order_id}- washing completed")


    def spoon_onto_tray(self):
        # Simulate spooning onto tray time
        trays = self.quantity // 12 + (1 if self.quantity % 12 > 0 else 0)
        time.sleep(trays * self.spoon_onto_tray_time)
        logging.info(f"Order:{self.order_id}- spooning completed")

    def bake(self):
        # Simulate baking time
        trays = self.quantity // 12 + (1 if self.quantity % 12 > 0 else 0)
        time.sleep(trays * self.bake_time)
        logging.info(f"Order:{self.order_id}- baking completed")

    def cool(self):
        # Simulate cooling time
        time.sleep(self.cool_time)
        logging.info(f"Order:{self.order_id}- cooling completed")

    def pack_and_payment(self):
        # Simulate packing and payment time
        trays = self.quantity // 12 + (1 if self.quantity % 12 > 0 else 0)
        time.sleep(trays * self.pack_and_payment_time)
        logging.info(f"Order:{self.order_id}- packing completed")

    def process_order(self, inventory):
        try:
            start_time = time.time()
            if inventory.remove_stock(self.cookie_type, self.quantity):
                # Simulate order processing time
                self.wash_and_mix()
                self.spoon_onto_tray()
                self.bake()
                self.cool()
                self.pack_and_payment()
                self.status = 'Completed'
                self.processing_time = time.time() - start_time
                logging.info(f"Order {self.order_id} for {self.quantity} {self.cookie_type} cookies completed in {self.processing_time:.2f} seconds.")
            else:
                self.status = 'Failed'
                logging.error(f"Order {self.order_id} failed due to insufficient inventory.")
        except Exception as e:
            self.status = 'Error'
            logging.error(f"Order {self.order_id} encountered an error: {e}")

class Inventory:
   
    def __init__(self):
        self.items = {'Chocolate Chip': 50, 'Sugar': 50, 'Peanut Butter': 50}
        self.lock = threading.Lock()

    def remove_stock(self, cookie_type, quantity):
        with self.lock:
            if self.items.get(cookie_type, 0) >= quantity:
                self.items[cookie_type] -= quantity
                return True
            return False

    def add_stock(self, cookie_type, quantity):
        with self.lock:
            self.items[cookie_type] = self.items.get(cookie_type, 0) + quantity
            logging.info(f"Added {quantity} {cookie_type} cookies to inventory.")

    def show_inventory(self):
        with self.lock:
            logging.info("Current Inventory:")
            for cookie_type, quantity in self.items.items():
                logging.info(f"{cookie_type}: {quantity} cookies left")

    def restock(self, restock_threshold=20, restock_amount=30):
        with self.lock:
            for cookie_type, quantity in self.items.items():
                if quantity < restock_threshold:
                    self.items[cookie_type] += restock_amount
                    logging.info(f"Restocked {restock_amount} {cookie_type} cookies.")

    

class CookieStore:
    
    def __init__(self, num_workers=3):
        self.order_queue = PriorityQueue()
        self.inventory = Inventory()
        self.workers = num_workers
        self.executor = ThreadPoolExecutor(max_workers=self.workers)
        self.shutdown_event = threading.Event()
        self.total_orders = 0
        self.completed_orders = 0
        self.total_orders_lock = threading.Lock()  # Lock for updating total_orders safely
        self.completed_orders_lock = threading.Lock()

    def adjust_workers(self, target_workers):
        if target_workers != self.workers:
            self.executor._max_workers = target_workers
            self.workers = target_workers
            logging.info(f"Adjusted number of workers to {target_workers}.")

    def take_order(self, order):
        if self.inventory.remove_stock(order.cookie_type, order.quantity):
            self.order_queue.put(order)
            logging.info(f"Received order {order.order_id} for {order.quantity} {order.cookie_type} cookies.")
        else:
            logging.error(f"Order {order.order_id} cannot be placed due to insufficient inventory.")

    def process_orders(self):
        while not self.shutdown_event.is_set() or not self.order_queue.empty():
            try:
                order = self.order_queue.get(timeout=1)
                with self.total_orders_lock:  # Protect the update to total_orders
                    self.total_orders += 1
                future = self.executor.submit(order.process_order, self.inventory)
                future.add_done_callback(self._increment_completed_orders)
            except Empty:
                continue

        self.executor.shutdown(wait=True)
        logging.info(f"All orders processed. Total: {self.total_orders}, Completed: {self.completed_orders}.")

    def _increment_completed_orders(self, _):
        with self.completed_orders_lock:  # Protect the update to completed_orders
            self.completed_orders += 1


    def start_processing(self):
        processing_thread = threading.Thread(target=self.process_orders)
        processing_thread.start()
        return processing_thread
    

    def close_store(self):
        self.shutdown_event.set()
  
def fetch_email_orders(service, user_id='me'):
    logging.info("start")
    email_orders = []
    try:
        # Fetch only unread messages from the inbox with the label 'ORDER'
        response = service.users().messages().list(userId=user_id, q="").execute()
        messages = response.get('messages', [])
        logging.info(f"1-{messages}")
        for message in messages:
            # Fetch the message
            msg = service.users().messages().get(userId=user_id, id=message['id'], format='metadata', metadataHeaders=['Subject']).execute()
            # Extract subject which contains the order details
            headers = msg['payload']['headers']
            subject = next(header['value'] for header in headers if header['name'] == 'Subject')
            
            # Assuming subject format is "customer_id, cookie_type, quantity"
            order_details = subject.split(',')
            logging.info(f"1-{order_details}")
            if len(order_details) == 3:
                customer_id, cookie_type, quantity = order_details
                email_orders.append(Order(customer_id, cookie_type, int(quantity)))
                # Optionally mark the message as read after processing
                # service.users().messages().modify(userId=user_id, id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()
        
    except error.HttpError as error:
        print(f'An error occurred: {error}')
    
    return email_orders


def simulate_customer_activity(store, num_customers=10, simulation_duration=10, service=None):
    if service:
        # Fetch orders from email and add to store
        email_orders = fetch_email_orders(service)
        for order in email_orders:
            store.take_order(order)
            logging.info(f"Email Customer {order.order_id} placed order {order.order_id}.")


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def gmail_authenticate():
    creds = None
    if os.path.exists('token2.pickle'):
        with open('token2.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token2.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds



def main():
    store = CookieStore()

    creds = gmail_authenticate()
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)

    store = CookieStore()

    # Simulate customer activity including email orders
    simulate_customer_activity(store, num_customers=10, simulation_duration=10, service=service)

    # Simulate adding new stock
    store.inventory.add_stock('Chocolate Chip', 20)

    # Start processing orders in a separate thread
    processing_thread = store.start_processing()

    # Simulate customer activity
    simulate_customer_activity(store, num_customers=10)

    # Simulate end of day restocking
    store.inventory.restock()

    # Adjust workers based on end of day processing if necessary
    store.adjust_workers(target_workers=5)

    # Simulate end of the day by waiting for all customer activity to finish
    # and closing the store to new orders
    store.close_store()

    # Wait for the processing thread to finish
    processing_thread.join()

    # Show final inventory
    store.inventory.show_inventory()

    # Print performance metrics
    logging.info(f"Total Orders: {store.total_orders}")
    logging.info(f"Completed Orders: {store.completed_orders}")
    # Additional detailed performance metrics can be added here as needed

if __name__ == "__main__":
    main()
