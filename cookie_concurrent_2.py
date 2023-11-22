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
from abc import ABC, abstractmethod


class Cookiestore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Cookiestore, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.handler_chain = None
            self.order_queue = PriorityQueue()
            self.inventory = Cookiestore.Inventory()
            self.shutdown_event = threading.Event()
            self.total_orders = 0
            self.completed_orders = 0
            self.total_orders_lock = threading.Lock()  # Lock for updating total_orders safely
            self.completed_orders_lock = threading.Lock()
            self.initialized = True
            #time
            self.wash_and_mix_time = 6  
            self.spoon_onto_tray_time = 2  
            self.bake_time = 10  
            self.cool_time = 5  
            self.pack_and_payment_time = 3
            #trays
            self.wash_and_mix_n_trays = 3
            self.spoon_onto_tray_trays = 1
            self.baking_trays = 1
            self.cooling_trays = 99
            self.pack_and_payment_trays = 1
        
        self.order_processing_times = {
            'wash_and_mix_time': 6,
            'spoon_onto_tray_time': 2,
            'bake_time': 10,
            'cool_time': 5,
            'pack_and_payment_time': 3
        }
            

    class Inventory:
        _instance = None

        def __new__(cls):
            if cls._instance is None:
                cls._instance = super(Cookiestore.Inventory, cls).__new__(cls)
            return cls._instance
        
        def __init__(self, num_workers=3):
            if not hasattr(self, 'initialized'):
                self.items = {'Chocolate Chip': 50, 'Sugar': 50, 'Peanut Butter': 50}
                self.lock = threading.Lock()
                self.initialized = True
    
    
    
    class Order:
        def __init__(self, order_id, cookie_type, quantity, priority=100):
            self.order_id = order_id
            self.cookie_type = cookie_type
            self.quantity = quantity
            self.priority = priority
            self.status = 'Pending'
            self.start_time = None 
            store = Cookiestore()
            self.wash_and_mix_time = store.order_processing_times['wash_and_mix_time']
            self.spoon_onto_tray_time = store.order_processing_times['spoon_onto_tray_time']
            self.bake_time = store.order_processing_times['bake_time']
            self.cool_time = store.order_processing_times['cool_time']
            self.pack_and_payment_time = store.order_processing_times['pack_and_payment_time']

        def set_start_time(self, start_time):
            self.start_time = start_time

        def calculate_total_time(self):
            return time.time() - self.start_time
    
    class Handler(ABC):
        def __init__(self) -> None:
            self.successor = None

        def set_successor(self, successor):
            self.successor = successor

        @abstractmethod
        def handle_request(self, request):
            pass
    
    
    class Ordertaker(Handler):
        
        def __init__(self) -> None:
            super().__init__()
            self.orders = None
            self.orders_lock = threading.Lock()
        
        def run(self):
            orders = self.load_orders()
        
        def load_orders(self):
            self.orders = [Cookiestore.Order("artur", "Chocolate Chip", 3), Cookiestore.Order("CookieMonster", "Chocolate Chip", 4),Cookiestore.Order("Maxima", "Chocolate Chip", 7), Cookiestore.Order("Nick", "Chocolate Chip", 6)]
            return self.orders
        
        def handle_request(self):
            orders = self.load_orders()
            while True:
                if len(orders) > 0:
                    time.sleep(1)
                    order = orders.pop(0)
                    
                    order_thread = threading.Thread(target=self.pass_order, args=(order,))
                    order_thread.start()
                else:
                    print("no more orders")
                    break
            
        def pass_order(self, order):
            order.set_start_time(time.time())  # Set the start time for the order
            self.successor.handle_request(order)  


        
    class Employee1(Handler):

        def __init__(self) -> None:
            super().__init__()
            self.available = threading.Lock()
            

        def wash_and_mix(self,order):
            #Calculate actual time
            time.sleep(order.wash_and_mix_time)
            print(f"Order:{order.order_id}- washing completed")
            #logging.info(f"Order:{self.order_id}- washing completed")


        def spoon_onto_tray(self,order):
           # trays = self.quantity // 12 + (1 if self.quantity % 12 > 0 else 0)
            #Simulate spooning onto tray time
            time.sleep(order.spoon_onto_tray_time)
            print(f"Order:{order.order_id}- spooning completed")
            #logging.info(f"Order:{order.order_id}- spooning completed")

        def handle_request(self, order):
                    self.available.acquire()
                    Cookiestore.Inventory().items[order.cookie_type] += -order.quantity
                    print(f"There are {Cookiestore.Inventory().items[order.cookie_type]} of type {order.cookie_type} left")
                    self.wash_and_mix(order)
                    self.spoon_onto_tray(order)
                    self.available.release()
                    self.successor.handle_request(order)
                    #self.available = True
        

    class Oven(Handler):
        def __init__(self) -> None:
            super().__init__()
            self.available = True
            self.available = threading.Lock()
        
        def baking(self,order):
            time.sleep(order.bake_time)
            print(f"Order:{order.order_id}- baking completed")
        
        def handle_request(self, order):
                    self.available.acquire()  
                    self.baking(order)
                    self.available.release()
                    self.successor.handle_request(order)
    

    class Employee2(Handler):
        def __init__(self) -> None:
            super().__init__()
            self.available = threading.Lock()

        def cool(self, order):
            # Calculate actual cooling time
            time.sleep(order.cool_time)
            print(f"Order:{order.order_id}- cooling completed")
            # Note: No need for logging here as print is already used

        def pack_and_payment(self, order):
            # Simulate packing and payment time
            time.sleep(order.pack_and_payment_time)
            print(f"Order:{order.order_id}- packing and payment completed")

        def handle_request(self, order):
            # Start cooling without locking the resource
            threading.Thread(target=self.cool, args=(order,)).start()
            # Wait for cooling to complete before proceeding with packing and payment
            time.sleep(order.cool_time)
            self.pack_and_payment(order)
            if self.successor is not None:
                self.successor.handle_request(order)

                    

    class OrderDelivery(Handler):

        def __init__(self) -> None:
            super().__init__()
            self.available = True

        def handle_request(self, order):
            total_time = order.calculate_total_time()
            print(f"Order:{order.order_id} completed in {total_time:.2f} seconds")
            self.calculate_and_print_price(order)

        def calculate_and_print_price(self, order):
            price_per_cookie = 0.5  # Example price per cookie
            total_price = price_per_cookie * order.quantity
            print(f"Price for Order {order.order_id}: ${total_price:.2f}")


    
    def run(self):
        inventory = Cookiestore.Inventory()

        self.handler_chain = Cookiestore.Ordertaker()
        self.handler_chain.set_successor(Cookiestore.Employee1())

        self.handler_chain.successor.set_successor(Cookiestore.Oven())
        self.handler_chain.successor.successor.set_successor(Cookiestore.Employee2())
        self.handler_chain.successor.successor.successor.set_successor(Cookiestore.OrderDelivery())

        self.handler_chain.handle_request()



my_cookiestore = Cookiestore()
my_cookiestore.run()


    
        

    
 

                