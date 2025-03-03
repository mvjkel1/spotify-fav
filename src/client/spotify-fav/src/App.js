import React, { useState } from 'react';
import './App.css';

function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleLoginClick = () => {
    setLoading(true);
    setError(null);

    fetch('http://localhost:8000/user-auth/login')
      .then((response) => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then((data) => {
        if (data.login_url) {
          window.location.href = data.login_url;
        } else {
          throw new Error('Login URL not found');
        }
      })
      .catch((error) => {
        setError(error);
        setLoading(false);
      });
  };

  return (
    <div className="App">
      <header className="App-header">
        <p>Click the button below to login with Spotify:</p>
        <button onClick={handleLoginClick} disabled={loading}>
          {loading ? 'Generating Login URL...' : 'Login with Spotify'}
        </button>
        {error && <div style={{ color: 'red' }}>Error: {error.message}</div>}
      </header>
    </div>
  );
}

export default App;
