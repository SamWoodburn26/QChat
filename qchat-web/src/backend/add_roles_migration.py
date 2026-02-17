#Migration Script: Add 'role' field to all existing users in chatbot_db
from db_connection import Database
from datetime import datetime

def migrate_add_roles():
    print("MIGRATION: Adding 'role' field to all users") 
    # Connect to MongoDB
    db = Database()
    db.connect()
    
    # Access chatbot_db directly
    chatbot_db = db._client["chatbot_db"]
    users_collection = chatbot_db["users"]
    
    print(f"Connected to: chatbot_db")
    
    # Count users without role
    count = users_collection.count_documents({"role": {"$exists": False}})
    print(f"Found {count} users without 'role' field\n")
    
    if count == 0:
        print("All users already have 'role' field!")
        print("\n Current users:")
        all_users = users_collection.find({}, {"username": 1, "role": 1, "_id": 0}).limit(10)
        for user in all_users:
            role = user.get('role', ' NO ROLE')
            print(f"   - {user.get('username', 'N/A')}: {role}")
        return
    
    # Show preview
    print("👥 Users that will be updated:")
    preview = users_collection.find(
        {"role": {"$exists": False}}, 
        {"username": 1, "_id": 0}
    ).limit(5)
    for user in preview:
        print(f"   - {user.get('username', 'N/A')}")
    if count > 5:
        print(f"   ... and {count - 5} more")
    print()
    
    # Confirm
    confirm = input(" Add 'role: student' to these users? (yes/no): ")
    
    if confirm.lower() != "yes":
        print(" Migration cancelled")
        return
    
    # Update all users
    result = users_collection.update_many(
        {"role": {"$exists": False}},
        {
            "$set": {
                "role": "student",
                "updatedAt": datetime.utcnow()
            }
        }
    )
    
    print(f"\n Updated {result.modified_count} users")
    print("   All users now have 'role: student'\n")
    
    # Show results
    print(" Updated users:")
    updated = users_collection.find({}, {"username": 1, "role": 1, "_id": 0}).limit(10)
    for user in updated:
        print(f"   - {user.get('username', 'N/A')}: {user.get('role', 'N/A')}")
    
    print(" MIGRATION COMPLETED!")
  
def make_user_admin(username: str):
    db = Database()
    db.connect()
    
    # Access chatbot_db directly
    chatbot_db = db._client["chatbot_db"]
    users_collection = chatbot_db["users"]
    
    # Check if user exists
    user = users_collection.find_one({"username": username})
    if not user:
        print(f" User '{username}' not found in chatbot_db")
        return
    
    # Update to admin
    result = users_collection.update_one(
        {"username": username},
        {
            "$set": {
                "role": "admin",
                "updatedAt": datetime.utcnow()
            }
        }
    )
    
    if result.modified_count > 0:
        print(f" {username} is now ADMIN")
    else:
        print(f"  {username} is already ADMIN")


if __name__ == "__main__":

    migrate_add_roles()
    print("\nTo make a user admin, run:")
    print('   python3 -c \'from add_roles_migration import make_user_admin; make_user_admin("trua")\'')
    print()