import { useState } from 'react';

function App() {
  const [userInput, setUserInput] = useState('');
  const [botResponse, setBotResponse] = useState('');
  const [loading, setLoading] = useState(false);

  // handle the submit button click
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
      setBotResponse('Error communicating with server.');
      console.error(error);
    } finally {
      setLoading(false);
    }
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

      <div style={{ marginTop: '20px', backgroundColor: '#f5f5f5', padding: '15px', borderRadius: '5px' }}>
        {botResponse && <p><strong>Bot:</strong> {botResponse}</p>}
      </div>
    </div>
  );
}

export default App;
