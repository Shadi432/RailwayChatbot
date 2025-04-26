import { useState } from 'react';
import './App.css';

function App() {
  const [userInput, setUserInput] = useState('');
  const [botResponse, setBotResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!userInput.trim()) return;

    setLoading(true);

    try {
      const response = await fetch('http://localhost:5000/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userInput }),
      });

      const data = await response.json();
      setBotResponse(data.response || 'No response from server.');
    } catch (error) {
      console.error('Fetch error:', error);
      setBotResponse('Error communicating with server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chatbot-container">
      <h1>Train Delay Chatbot</h1>

      <input
        type="text"
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSubmit();
        }}
        placeholder="Type something like: delay from Norwich to London at 9am tomorrow"
      />

      <button onClick={handleSubmit} disabled={loading}>
        {loading ? 'Thinking...' : 'Ask'}
      </button>

      <div className="response-box">
        {botResponse && (
          <p><strong>Bot:</strong> {botResponse}</p>
        )}
      </div>
    </div>
  );
}

export default App;
