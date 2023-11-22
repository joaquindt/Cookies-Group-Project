import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import PriorityQueue
import time
import random
from queue import Empty


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Order:
    def __init__(self, order_id, cookie_type, quantity, priority=100):
        self.order_id = order_id
        self.cookie_type = cookie_type
        self.quantity = quantity
        self.priority = priority
        self.status = 'Pending'
        self.processing_time = None

    def __lt__(self, other):
        return self.priority < other.priority

    def process_order(self, inventory):
        try:
            start_time = time.time()
            if inventory.remove_stock(self.cookie_type, self.quantity):
                # Simulate order processing time
                time.sleep(random.uniform(0.5, 1.5))
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
  


def simulate_customer_activity(store, num_customers=10, simulation_duration=10):
    end_time = time.time() + simulation_duration
    customer_id = 1

    while time.time() < end_time and customer_id <= num_customers:
        # Randomly create orders
        cookie_types = list(store.inventory.items.keys())
        cookie_type = random.choice(cookie_types)
        quantity = random.randint(1, 6)  # Random quantity between 1 and 6
        priority = random.randint(1, 100)  # Random priority

        # Create a new order
        order = Order(customer_id, cookie_type, quantity, priority)
        store.take_order(order)
        logging.info(f"Customer {customer_id} placed order {order.order_id}.")

        # Increment customer_id for the next order
        customer_id += 1

        # Random wait time to simulate time between customers placing orders
        time.sleep(random.uniform(0.5, 2.0))

    logging.info("Customer activity simulation completed.")


def main():
    store = CookieStore()

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

