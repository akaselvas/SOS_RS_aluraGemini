import os

# Be careful with this, it deletes the database file
if os.path.exists("/tmp/test.db"):
    os.remove("/tmp/test.db")
else:
    print("The database file does not exist")
