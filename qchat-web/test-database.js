//Test whether CRUD operations are working in the database.
import { MongoClient } from "mongodb";
import dotenv from "dotenv";

dotenv.config();

const uri = process.env.MONGO_URI;
const client = new MongoClient(uri);

async function testDatabaseOperations() {
  try {
    console.log("Testing Database Operations...\n");

    await client.connect();
    console.log("Connected to MongoDB\n");

    const db = client.db("qchat");
    const chatLogs = db.collection("chatLogs");
    const universityInfo = db.collection("universityInfo");
    
    //Perform 8 tests on the universityInfo and chatLogs collections respectively 
    //(category retrieval, search, addition, listing, retrieval by category, statistics, update, cleanup)
    // Test 1: Get all categories
    console.log("Testing 1: Get All Categories");
    const categories = await universityInfo.distinct("category");
    console.log(`Found ${categories.length} categories:`, categories);
    console.log("");

    // Test 2: Search university info
    console.log("Testing 2: Search University Info");
    // const ==constant
    const searchQuery = "library";
    const searchResults = await universityInfo.find({
      $or: [
        //case-insensitive search
        { question: { $regex: searchQuery, $options: "i" } },
        { answer: { $regex: searchQuery, $options: "i" } },
        { keywords: { $regex: searchQuery, $options: "i" } }
      ]
    }).toArray();
    console.log(`Search for "${searchQuery}": Found ${searchResults.length} results`);
    searchResults.forEach((result, index) => {
      console.log(` ${index + 1}. ${result.question}`);
    });
    console.log("");

    // Test 3: Insert new chat log
    console.log("Testing 3: Insert Chat Log");
    const newChatLog = {
      userId: "test_user_999",
      message: "How do I apply for financial aid?",
      response: "Complete the FAFSA at fafsa.gov.",
      timestamp: new Date(),
      category: "Financial Aid",
      sessionId: "test_session_001"
    };
    const insertResult = await chatLogs.insertOne(newChatLog);
    console.log(`Chat log inserted with ID: ${insertResult.insertedId}`);
    console.log("");

    // Test 4: Get user chat history
    console.log("Testing 4: Get User Chat History");
    const userLogs = await chatLogs.find({ userId: "student123" })
      .sort({ timestamp: -1 })
      .toArray();
    console.log(`Found ${userLogs.length} chat logs for student123:`);
    userLogs.forEach((log, index) => {
      console.log(`   ${index + 1}. ${log.message}`);
    });
    console.log("");

    // Test 5: Get info by category
    console.log("Testing 5: Get Info by Category");
    const category = "Academics";
    const categoryResults = await universityInfo.find({ 
      category: { $regex: category, $options: "i" } 
    }).toArray();
    console.log(`   Found ${categoryResults.length} items in "${category}" category:`);
    categoryResults.forEach((item, index) => {
      console.log(`   ${index + 1}. ${item.question}`);
    });
    console.log("");

    // Test 6: Statistics
    console.log("Testing 6: Database Statistics");
    const totalChats = await chatLogs.countDocuments();
    const totalInfo = await universityInfo.countDocuments();
    
    // Recent chats (last 24 hours)
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const recentChats = await chatLogs.countDocuments({
      timestamp: { $gte: yesterday }
    });

    console.log("Statistics:");
    console.log(`-Total Chat Logs: ${totalChats}`);
    console.log(`-Total University Info: ${totalInfo}`);
    console.log(`-Recent Chats (24h): ${recentChats}`);
    console.log(`-Total Categories: ${categories.length}`);
    console.log("");

    // Test 7: Update university info
    console.log("Testing 7: Update University Info");
    const updateResult = await universityInfo.updateOne(
      { category: "Library" },
      { 
        $set: { 
          updatedAt: new Date(),
          keywords: ["library", "hours", "open", "schedule", "study", "updated"]
        }
      }
    );
    console.log(`Updated ${updateResult.modifiedCount} document(s)`);
    console.log("");

    // Test 8: Cleanup test data
    console.log("Testing 8: Cleanup Test Data");
    const deleteResult = await chatLogs.deleteMany({ userId: "test_user_999" });
    console.log(`Deleted ${deleteResult.deletedCount} test chat log(s)`);
    console.log("");

    console.log("All tests completed successfully!");
  } catch (error) {
    console.error("Test failed:", error);
  } finally {
    await client.close();
    console.log("\nDatabase connection closed");
  }
}

testDatabaseOperations();

