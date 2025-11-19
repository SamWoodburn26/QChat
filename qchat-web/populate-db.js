import { MongoClient } from "mongodb";
import dotenv from "dotenv";

// Load environment variables from .env file
dotenv.config({ debug: true });

const uri = process.env.MONGO_URI;
//It s create MongoClient but its not connected yet network 
//because i did not call client.connect() yet
const client = new MongoClient(uri);

const sampleUniversityInfo = [
  {
    category: "Academics",
    question: "How do I register for classes?",
    answer: "You can register for classes through the self-service portal. Log in with your username,and choose 'student planing 'from home page , select the term, and search for available courses and you can Register from here .",
    keywords: ["register", "classes", "course", "enrollment", "self-service","Student planing"]
  },
  {
    category: "Financial Aid",
    question: "When is the tuition deadline?",
    answer: "Tuition payment deadlines vary by semester. Fall semester deadline is typically August 15th, Spring semester is January 15th. Check the academic calendar for exact dates.",
    keywords: ["tuition", "payment", "deadline", "financial", "fees"]
  },
  {
    category: "Campus Life",
    question: "What dining options are available on campus?",
    answer: "The campus offers multiple dining options including the Main Cafeteria, Food Court, Starbucks, and various food trucks. Meal plans are available for purchase.",
    keywords: ["dining", "food", "cafeteria", "meal plan", "restaurant"]
  },
  {
    category: "Library",
    question: "What are the library hours?",
    answer: "The main library is open Monday-Thursday 7:30 AM - 11:00 PM, Friday 7:30 AM - 6:00 PM, Saturday 10:00 AM - 6:00 PM, and Sunday 12:00 PM - 11:00 PM.",
    keywords: ["library", "hours", "open", "schedule", "study"]
  },
  {
    category: "IT Services",
    question: "How do I reset my password?",
    answer: "To reset your password, visit the IT Help Desk portal at helpdesk.university.edu or call (555) 123-4567. You'll need your student ID to verify your identity.",
    keywords: ["password", "reset", "login", "account", "IT", "help desk"]
  }
];

async function populateDatabase() {
  try {
    await client.connect();
    console.log("Connected to MongoDB");

    //create an access to DB named qchat
    const db = client.db("qchat");
    
    // Clear existing data (optional - remove in production)
    console.log("\nClearing existing data...");
    await db.collection("universityInfo").deleteMany({});
    await db.collection("chatLogs").deleteMany({});
    
    // Insert sample university info
    console.log("\nInserting sample university information...");
    const result = await db.collection("universityInfo").insertMany(sampleUniversityInfo);
    console.log(`Inserted ${result.insertedCount} documents into universityInfo`);
    
    // Insert sample chat logs
    console.log("\nInserting sample chat logs...");
    const sampleChatLogs = [
      {
        userId: "student123",
        message: "How do I register for classes?",
        response: "You can register through the self-service portal.",
        timestamp: new Date(),
        category: "Academics"
      },
      {
        userId: "student456",
        message: "What are the library hours?",
        response: "The library is open Monday-Thursday 7:30 AM - 11:00 PM.",
        timestamp: new Date(),
        category: "Library"
      }
    ];
    // Chat logs are being added using insertMany, 
    // and the number of documents added is being logged. 
    const chatResult = await db.collection("chatLogs").insertMany(sampleChatLogs);
    console.log(`Inserted ${chatResult.insertedCount} chat logs`);
    
    // Verify the data
    console.log("\nDatabase Statistics:");
    const infoCount = await db.collection("universityInfo").countDocuments();
    const logCount = await db.collection("chatLogs").countDocuments();
    console.log(`University Info: ${infoCount} documents`);
    console.log(`Chat Logs: ${logCount} documents`);
    
    console.log("\nDatabase populated successfully!");

  } catch (error) {
    console.error("Error:", error);
  } finally {
    await client.close();
    console.log("\nConnection closed");
  }
}

populateDatabase();

