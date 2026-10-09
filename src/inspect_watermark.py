import requests


url = "https://dummyjson.com/products/1"

response = requests.get(
    url,
    timeout=30
)

response.raise_for_status()

product = response.json()

print("Product ID:")
print(product["id"])

print("\nProduct title:")
print(product["title"])

print("\nMeta:")
print(product["meta"])

print("\nUpdated at:")
print(product["meta"]["updatedAt"])