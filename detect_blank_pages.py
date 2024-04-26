import os

directory = "./logs"

for filename in os.listdir(directory):
    filepath = os.path.join(directory, filename)
    if os.path.isfile(filepath) and os.path.getsize(filepath) < 1126400:
        os.remove(filepath)
