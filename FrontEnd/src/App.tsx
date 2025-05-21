import { useState } from 'react';
import axios from 'axios';

function App() {
  const [userInput, setUserInput] = useState('');
  const [botResponse, setBotResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null); // <-- Add this

  // handle the submit button click
  const handleSubmit = async () => {
    const trimmedInput = userInput.trim();
    setLoading(true);

    await axios.post('http://localhost:5000/chatbot', 
      { message: trimmedInput, session_id: sessionId }, // <-- Send session_id
      {
        headers: {
          "Content-Type": "application/json"
        }
      }
    )
    .then((response) => {
      setBotResponse(response.data["response"]);
      setSessionId(response.data["session_id"]); // <-- Store session_id for next turn
      setUserInput(""); // <-- This will clear the input bar after sending
    })
    .catch((err) => {
      console.log(err);
      setBotResponse('Error communicating with server.');
    })
    .finally(() => setLoading(false));
  };

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '20px', fontFamily: 'Arial' }}>
      <h1>Train Delay Chatbot</h1>

      <input
        type="text"
        value={userInput}
        placeholder="Type your question..."
        onChange={(e) => setUserInput(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        style={{ width: '100%', padding: '10px', fontSize: '16px' }}
      />

      <button
        onClick={handleSubmit}
        disabled={loading}
        style={{ marginTop: '10px', padding: '10px 20px', fontSize: '16px' }}
      >
        {loading ? 'Thinking...' : 'Ask'}
      </button>

      <div style={{ marginTop: '20px', backgroundColor: '#574f4f', padding: '15px', borderRadius: '5px' }}>
        {botResponse && <p><strong>Bot:</strong> {botResponse}</p>}
      </div>
    </div>
  );
}

export default App;
