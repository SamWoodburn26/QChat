/**
 * User Profile Integration Example
 * 
 * This file shows how to integrate the user profile system with the frontend.
 * Add these functions to your chat component or create a separate profile service.
 */

const API_BASE_URL = 'http://localhost:7071/api'; // Update with your backend URL

// ===== Profile API Functions =====

/**
 * Get user profile
 */
export async function getUserProfile(username: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/profile?username=${encodeURIComponent(username)}`);
    if (!response.ok) {
      throw new Error(`Failed to get profile: ${response.status}`);
    }
    const data = await response.json();
    return data.profile;
  } catch (error) {
    console.error('Error fetching profile:', error);
    return null;
  }
}

/**
 * Update user profile fields
 */
export async function updateProfile(username: string, updates: Record<string, any>) {
  try {
    const response = await fetch(`${API_BASE_URL}/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        action: 'update',
        data: updates,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update profile: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error updating profile:', error);
    throw error;
  }
}

/**
 * Add a class to user's schedule
 */
export async function addClass(username: string, classData: {
  name: string;
  code?: string;
  professor?: string;
  schedule?: string;
  location?: string;
}) {
  try {
    const response = await fetch(`${API_BASE_URL}/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        action: 'add_class',
        data: classData,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to add class: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error adding class:', error);
    throw error;
  }
}

/**
 * Add extracurricular activity
 */
export async function addActivity(username: string, activity: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        action: 'add_activity',
        data: { activity },
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to add activity: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error adding activity:', error);
    throw error;
  }
}

/**
 * Set user preferences
 */
export async function setPreferences(username: string, preferences: {
  favorite_dining_halls?: string[];
  dietary_restrictions?: string[];
  study_locations?: string[];
}) {
  try {
    const response = await fetch(`${API_BASE_URL}/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        action: 'set_preferences',
        data: preferences,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to set preferences: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error setting preferences:', error);
    throw error;
  }
}

// ===== Modified Chat Function =====

/**
 * Send a chat message with username for profile integration
 */
export async function sendMessage(message: string, username: string) {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        username,  // <-- Pass username to enable profile features
        userId: username,  // For backward compatibility
        action: 'chat',
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
}

// ===== React Component Example =====

/**
 * Example React component showing profile integration
 */
/*
import React, { useState, useEffect } from 'react';

function ProfileExample() {
  const [profile, setProfile] = useState(null);
  const [username, setUsername] = useState('student123'); // Get from auth context
  
  useEffect(() => {
    loadProfile();
  }, [username]);
  
  async function loadProfile() {
    const userProfile = await getUserProfile(username);
    setProfile(userProfile);
  }
  
  async function handleAddClass() {
    await addClass(username, {
      name: 'Introduction to Programming',
      code: 'CS101',
      professor: 'Dr. Smith',
      schedule: 'MWF 10:00-11:00',
      location: 'Science Building Room 201'
    });
    loadProfile(); // Refresh profile
  }
  
  async function handleUpdateMajor(major: string) {
    await updateProfile(username, {
      'personal_info.major': major
    });
    loadProfile(); // Refresh profile
  }
  
  async function handleSetDietaryRestrictions(restrictions: string[]) {
    await setPreferences(username, {
      dietary_restrictions: restrictions
    });
    loadProfile(); // Refresh profile
  }
  
  return (
    <div>
      <h2>My Profile</h2>
      {profile && (
        <div>
          <p>Name: {profile.personal_info?.name || 'Not set'}</p>
          <p>Year: {profile.personal_info?.year || 'Not set'}</p>
          <p>Major: {profile.personal_info?.major || 'Not set'}</p>
          
          <h3>Classes</h3>
          <ul>
            {profile.schedule?.classes?.map((cls, i) => (
              <li key={i}>
                {cls.code} - {cls.name}
                <br />
                {cls.schedule} in {cls.location}
              </li>
            ))}
          </ul>
          
          <h3>Activities</h3>
          <ul>
            {profile.schedule?.extracurriculars?.map((activity, i) => (
              <li key={i}>{activity}</li>
            ))}
          </ul>
          
          <h3>Preferences</h3>
          <p>Dietary: {profile.preferences?.dietary_restrictions?.join(', ') || 'None'}</p>
          <p>Favorite Dining: {profile.preferences?.favorite_dining_halls?.join(', ') || 'None'}</p>
        </div>
      )}
      
      <button onClick={handleAddClass}>Add Sample Class</button>
    </div>
  );
}
*/

// ===== Usage in Chat Component =====

/**
 * Example of integrating profile with existing chat
 */
/*
function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const username = useAuth(); // Get from your auth context
  
  async function handleSend() {
    if (!input.trim()) return;
    
    // Add user message
    setMessages(prev => [...prev, { role: 'user', text: input }]);
    
    // Send to backend (profile info will be extracted automatically)
    const response = await sendMessage(input, username);
    
    // Add bot response
    setMessages(prev => [...prev, {
      role: 'assistant',
      text: response.reply,
      sources: response.sources
    }]);
    
    setInput('');
  }
  
  return (
    <div>
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role}>
            {msg.text}
          </div>
        ))}
      </div>
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyPress={e => e.key === 'Enter' && handleSend()}
      />
      <button onClick={handleSend}>Send</button>
    </div>
  );
}
*/

// ===== Profile Settings Component Example =====

/**
 * Profile management interface
 */
/*
function ProfileSettings({ username }) {
  const [year, setYear] = useState('');
  const [major, setMajor] = useState('');
  const [dietaryRestrictions, setDietaryRestrictions] = useState([]);
  
  async function handleSave() {
    await updateProfile(username, {
      'personal_info.year': year,
      'personal_info.major': major,
    });
    
    await setPreferences(username, {
      dietary_restrictions: dietaryRestrictions,
    });
    
    alert('Profile saved!');
  }
  
  return (
    <div>
      <h2>Profile Settings</h2>
      
      <label>
        Year:
        <select value={year} onChange={e => setYear(e.target.value)}>
          <option value="">Select...</option>
          <option value="freshman">Freshman</option>
          <option value="sophomore">Sophomore</option>
          <option value="junior">Junior</option>
          <option value="senior">Senior</option>
          <option value="grad">Graduate</option>
        </select>
      </label>
      
      <label>
        Major:
        <input
          value={major}
          onChange={e => setMajor(e.target.value)}
          placeholder="e.g., Computer Science"
        />
      </label>
      
      <label>
        Dietary Restrictions:
        <div>
          {['Vegetarian', 'Vegan', 'Gluten-Free', 'Dairy-Free'].map(opt => (
            <label key={opt}>
              <input
                type="checkbox"
                checked={dietaryRestrictions.includes(opt.toLowerCase())}
                onChange={e => {
                  if (e.target.checked) {
                    setDietaryRestrictions([...dietaryRestrictions, opt.toLowerCase()]);
                  } else {
                    setDietaryRestrictions(dietaryRestrictions.filter(d => d !== opt.toLowerCase()));
                  }
                }}
              />
              {opt}
            </label>
          ))}
        </div>
      </label>
      
      <button onClick={handleSave}>Save Profile</button>
    </div>
  );
}
*/

export {};
