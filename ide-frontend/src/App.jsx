import React, { useState, useCallback, useRef } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { keymap } from '@codemirror/view';
import { autocompletion, startCompletion } from '@codemirror/autocomplete';
import useWebSocket from 'react-use-websocket';
import axios from 'axios';
import './App.css';

// --- Configuration ---
const SESSION_ID = "shared-session-123";
const WEBSOCKET_URL = `ws://localhost:8000/ws/${SESSION_ID}`;
const EXECUTE_URL = "http://localhost:8000/execute";
const AUTOCOMPLETE_URL = "http://localhost:8000/autocomplete";
// ---------------------

function App() {
  const [code, setCode] = useState('print("Hello, collaborative world!")');
  const [output, setOutput] = useState('');
  const [suggestion, setSuggestion] = useState('');
  const view = useRef(); // Ref to access the CodeMirror instance

  const { sendMessage, lastMessage, readyState } = useWebSocket(WEBSOCKET_URL, {
    onOpen: () => console.log('WebSocket connection established.'),
    shouldReconnect: (closeEvent) => true,
  });

  // Handle incoming messages from other users
  React.useEffect(() => {
    if (lastMessage !== null) {
      setCode(lastMessage.data);
    }
  }, [lastMessage]);

  // Fetches AI completion from the backend
  const fetchCompletion = async (currentCode) => {
    try {
      const response = await axios.post(AUTOCOMPLETE_URL, { code: currentCode });
      const newSuggestion = response.data.suggestion || '';
      setSuggestion(newSuggestion);
      // If we got a suggestion, manually trigger the autocomplete dropdown
      if (newSuggestion && view.current) {
        startCompletion(view.current.view);
      }
    } catch (error) {
      console.error("Autocomplete error:", error);
      setSuggestion('');
    }
  };

  // Handle local code changes and broadcast them
  const handleCodeChange = useCallback((value) => {
    setCode(value);
    setSuggestion(''); // Clear old suggestion on new input
    sendMessage(value);
  }, [sendMessage]);

  // Keymap for manual activation with Ctrl + Space
  const completionKeymap = keymap.of([{
    key: "Ctrl-Space",
    run: (view) => {
      fetchCompletion(view.state.doc.toString());
      return true; // Indicates we handled this key press
    },
  }]);

  // Handle code execution
  const handleRunCode = async () => {
    setOutput('Executing...');
    try {
      const response = await axios.post(EXECUTE_URL, { code });
      setOutput(response.data.output);
    } catch (error) {
      setOutput(`Error: ${error.message}`);
    }
  };

  // --- NEW: Handler for the suggestion button click ---
  const handleSuggestionClick = () => {
    fetchCompletion(code); // Use the current code from state
  };

  // Custom autocomplete source that displays the suggestion from our state
  const myCompletions = (context) => {
    if (suggestion) {
      return {
        from: context.pos,
        options: [{ label: suggestion, type: "ghost" }]
      };
    }
    return null;
  };

  const connectionStatus = {
    [0]: 'Connecting',
    [1]: 'Connected',
    [2]: 'Closing',
    [3]: 'Closed',
  }[readyState];

  return (
    <div className="app-container">
      <header>
        <h1>🐍 Python Real-Time IDE (with AI ✨)</h1>
        <div className="status">
          Connection Status: <span className={`status-${connectionStatus.toLowerCase()}`}>{connectionStatus}</span>
        </div>
      </header>
      <main>
        <div className="editor-container">
          <CodeMirror
            ref={view}
            value={code}
            height="500px"
            extensions={[
              python(),
              autocompletion({ override: [myCompletions] }),
              completionKeymap
            ]}
            onChange={handleCodeChange}
            theme="dark"
          />
          {/* --- NEW BUTTON ADDED HERE --- */}
          <div className="button-group">
            <button onClick={handleSuggestionClick} className="suggestion-button">
              Get Suggestion ✨
            </button>
            <button onClick={handleRunCode} className="run-button">
              ▶ Run Code
            </button>
          </div>
        </div>
        <div className="output-container">
          <h2>Output</h2>
          <pre>{output}</pre>
        </div>
      </main>
    </div>
  );
}

export default App;