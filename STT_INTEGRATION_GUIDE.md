# Speech-to-Text Integration Guide

## Overview

Your chatbot now has integrated Speech-to-Text (STT) functionality using Deepgram. The integration allows you to:

- **Speak to your chatbot** instead of typing
- **Enable/disable STT** via configuration
- **Automatic KeepAlive** during streaming responses to maintain connection without transcribing the assistant's voice
- **Hybrid input** - use both speech and keyboard simultaneously

## Configuration

### 1. Environment Setup
Set your Deepgram API key:
```bash
export DEEPGRAM_API_KEY="your_deepgram_api_key_here"
```

### 2. Client Configuration
Update `client/client_config.yaml`:
```yaml
server_path: /home/jack/NEW-BACKEND/server/server.py

# Speech-to-Text Configuration
stt:
  enabled: true                    # Enable/disable STT functionality
  api_key_env: "DEEPGRAM_API_KEY"  # Environment variable containing Deepgram API key
  model: "nova-2"                  # Deepgram model to use
  language: "en-US"                # Language for transcription
  utterance_end_ms: 1000           # Milliseconds to wait before considering utterance ended
  keepalive_interval: 3            # Seconds between keepalive messages during streaming responses
```

## How It Works

### Speech Recognition Flow
1. **Microphone constantly listens** while the chatbot is running
2. **Complete utterances are detected** using voice activity detection
3. **Final transcripts are submitted** automatically as if you typed them
4. **KeepAlive messages** are sent during assistant responses to maintain connection

### KeepAlive Feature
Based on the [Deepgram KeepAlive documentation](https://developers.deepgram.com/docs/audio-keep-alive):

- When the assistant starts streaming a response, STT switches to **KeepAlive mode**
- **Transcription is paused** (no audio processing) 
- **Periodic KeepAlive messages** maintain the WebSocket connection
- **Transcription resumes** when the assistant finishes responding
- **No extra costs** for transcribing silence or assistant speech

## Usage

### Running with STT Enabled
```bash
python -m client
```

Output will show:
```
🎤 Speech-to-Text enabled - speak into your microphone!
💬 You can also type messages or say 'exit', 'quit', or 'bye' to stop
```

### Running with STT Disabled
Set `stt.enabled: false` in config, then:
```bash
python -m client
```

### Hybrid Usage
- **Speak naturally** - complete sentences will be automatically submitted
- **Type when needed** - keyboard input still works
- **Mix both** - use whatever is more convenient

### Example Session
```
🎤 Speech-to-Text enabled - speak into your microphone!
💬 You can also type messages or say 'exit', 'quit', or 'bye' to stop

🎤 You (speech): What's the weather like today?
🤖 Assistant: I don't have access to real-time weather data...

Type (or speak): Tell me a joke
⌨️  You: Tell me a joke  
🤖 Assistant: Why don't scientists trust atoms? Because they make up everything!

🎤 You (speech): That was funny, thanks
🤖 Assistant: I'm glad you enjoyed it! Feel free to ask for more jokes anytime.
```

## Technical Details

### STT Implementation
- **Dedicated thread** for Deepgram operations to avoid blocking
- **Event-driven processing** with WebSocket callbacks
- **Robust error handling** and connection management
- **Clean resource cleanup** on exit

### KeepAlive Implementation
- **Automatic pause/resume** based on assistant response state
- **JSON KeepAlive messages** sent every 3 seconds (configurable)
- **Connection maintenance** without audio transcription costs
- **Thread-safe coordination** between STT and chat processing

### Error Handling
- **Graceful fallback** to text-only mode if STT fails to initialize
- **Connection recovery** attempts for network issues
- **Proper cleanup** on interruption or exit

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Enable/disable STT functionality |
| `api_key_env` | `"DEEPGRAM_API_KEY"` | Environment variable for API key |
| `model` | `"nova-2"` | Deepgram model (nova-2, nova, base) |
| `language` | `"en-US"` | Language code for transcription |
| `utterance_end_ms` | `1000` | Silence duration before utterance ends |
| `keepalive_interval` | `3` | Seconds between KeepAlive messages |

## Troubleshooting

### STT Won't Start
1. Check API key: `echo $DEEPGRAM_API_KEY`
2. Verify microphone permissions
3. Check network connectivity to Deepgram

### Audio Issues
1. Test microphone with other applications
2. Check system audio settings
3. Try different Deepgram models

### Connection Issues
1. Check internet connection
2. Verify Deepgram service status
3. Review logs for specific error messages

## Advanced Usage

### Custom Models
```yaml
stt:
  model: "nova-2"  # or "nova", "base", etc.
```

### Different Languages
```yaml
stt:
  language: "es"    # Spanish
  language: "fr"    # French
  language: "de"    # German
```

### Sensitivity Tuning
```yaml
stt:
  utterance_end_ms: 500   # More responsive (faster)
  utterance_end_ms: 2000  # Less sensitive (slower)
```

---

**Note**: This integration maintains backward compatibility - the chatbot works exactly the same with STT disabled. 