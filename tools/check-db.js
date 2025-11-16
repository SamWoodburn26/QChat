const { MongoClient } = require('mongodb');
const fs = require('fs');
const path = require('path');

function readLocalSettings() {
  try {
    const p = path.join(__dirname, '..', 'src', 'backend', 'local.settings.json');
    const raw = fs.readFileSync(p, 'utf8');
    const j = JSON.parse(raw);
    return j && j.Values ? j.Values : null;
  } catch (e) {
    return null;
  }
}

const env = process.env;
const args = process.argv.slice(2);

const local = readLocalSettings();
const uri = env.MONGO_URI || env.MONGODB_URI || args[0] || (local && (local.MONGO_URI || local.MONGODB_URI));
const dbName = env.DB_NAME || (local && local.DB_NAME) || 'qchat';

if (!uri) {
  console.error('MONGO_URI not found. Provide it via MONGO_URI env var, MONGODB_URI, as the first arg, or in src/backend/local.settings.json.');
  process.exit(1);
}

(async () => {
  const client = new MongoClient(uri);
  try {
    console.log('Connecting to MongoDB...');
    await client.connect();
    const db = client.db(dbName);

    const chatCount = await db.collection('chatLogs').countDocuments();
    console.log(`chatLogs count: ${chatCount}`);

    const recent = await db.collection('chatLogs')
      .find()
      .sort({ timestamp: -1 })
      .limit(5)
      .toArray();

    console.log('Recent chatLogs (up to 5):');
    recent.forEach((doc, i) => {
      console.log(`--- ${i + 1} ---`);
      console.log(JSON.stringify(doc, null, 2));
    });

    // show universityInfo count as well
    const infoCount = await db.collection('universityInfo').countDocuments();
    console.log(`universityInfo count: ${infoCount}`);

  } catch (err) {
    console.error('Error checking DB:', err.message);
    process.exitCode = 2;
  } finally {
    await client.close();
    console.log('Done.');
  }
})();
