import requests
import time

def run_test():
    print("Starting End-to-End Test...")
    
    # 1. Create Order
    print("1. Creating order...")
    checkout_payload = {
        "customer_id": "cust-1",
        "event_id": "event-001",
        "zone_name": "VIP Pit",
        "quantity": 2
    }
    response = requests.post("http://localhost:8002/checkout", json=checkout_payload)
    response.raise_for_status()
    order = response.json()
    order_id = order["id"]
    print(f"Created order: {order_id} with status {order['status']}")

    # 2. Pay Order
    print(f"2. Paying order {order_id}...")
    response = requests.post(f"http://localhost:8002/orders/{order_id}/pay")
    response.raise_for_status()
    order = response.json()
    print(f"Order status after payment: {order['status']}")

    # 3. Generate Tickets (Trigger RabbitMQ message)
    print("3. Generating tickets (this will publish to RabbitMQ)...")
    graphql_payload = {
        "query": f'mutation {{ generateTickets(orderId: "{order_id}") {{ id qrHash }} }}'
    }
    response = requests.post("http://localhost:8003/graphql", json=graphql_payload)
    response.raise_for_status()
    data = response.json()
    
    if "errors" in data:
        print(f"Error generating tickets: {data['errors']}")
        return
        
    tickets = data["data"]["generateTickets"]
    print(f"Generated {len(tickets)} tickets.")

    # 4. Wait for consumer to process
    print("Waiting 2 seconds for RabbitMQ consumer to process the message...")
    time.sleep(2)

    # 5. Check Order Status
    print("4. Checking final order status...")
    response = requests.get(f"http://localhost:8002/orders/{order_id}")
    response.raise_for_status()
    order = response.json()
    print(f"Final order status: {order['status']}")
    print(f"Delivered at: {order['delivered_at']}")
    
    if order['status'] == "DELIVERED":
        print("SUCCESS! Asynchronous messaging worked.")
    else:
        print("FAILED! Order status was not updated to DELIVERED.")

if __name__ == "__main__":
    run_test()