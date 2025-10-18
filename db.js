import { MongoClient } from "mongodb";
//Help connecting to MONGO DB
import dotenv from "dotenv";
// its helping to load the .env file with secter infos

// loads the env. file variables 
dotenv.config();

//Get the MongoDb connection from env.
const uri = process.env.MONGO_URI;

if (!uri) {
  console.error("MONGO_URI is not defined in .env file");
  process.exit(1);
}
//Create a new Mongo client
const client = new MongoClient(uri);

//async function to connect to the DB
async function connectDB() {
  try {
    // Connect to MongoDB
    await client.connect();
    console.log("Successfully connected to MongoDB!");

    // Test the connection
    const db = client.db("qchat");
    
    // ListCoolections is bring to all current collection 
    const collections = await db.listCollections().toArray();
    const collectionNames = collections.map(c => c.name);
    
    //if ChatLogs do not exist ,it is create one 
    if (!collectionNames.includes("chatLogs")) {
      await db.createCollection("chatLogs");
      console.log("Created 'chatLogs' collection");
    }
    
    if (!collectionNames.includes("universityInfo")) {
      await db.createCollection("universityInfo");
      console.log("Created 'universityInfo' collection");
    }

    // List all collections
    console.log("\nAvailable collections:");
    const allCollections = await db.listCollections().toArray();
    allCollections.forEach(col => {
      console.log(`  - ${col.name}`);
    });

    // Insert a test document to verify write access
    const testDoc = {
      message: "Test connection",
      timestamp: new Date(),
      type: "system"
    };
    
    const result = await db.collection("chatLogs").insertOne(testDoc);
    console.log("\nTest document inserted with ID:", result.insertedId);

    // Clean up test document
    await db.collection("chatLogs").deleteOne({ _id: result.insertedId });
    console.log("Test document cleaned up");

    console.log("\nDatabase setup completed successfully!");

  } catch (error) {
    console.error("Error connecting to MongoDB:", error.message);
    process.exit(1);
  } finally {
    // Close the connection
    await client.close();
    console.log("\nConnection closed");
  }
}

// Run the connection
connectDB();