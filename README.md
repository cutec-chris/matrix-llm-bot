Matrix LLM Bot
==================

Talk to most Large Language Models via any Matrix client!

# Usage
1. Create a room
2. Add the bot
3. Start chatting.

# Features
- Use in every room another Model
- any openai compatible api is useable (openai, groq, ollama ...)
- Answer in Threads (configureable)
- Shows typing indicator!
- Stores configureable amount of messages as context for conversations
- wake up Server per WOL on demand

# Planned Features
- comfui support (multiple workflows)
- scripting support (code snittpets can do anything you can do in chat, like RAG, Crews ...)

# Configure

Create a copy of the example `config.sample.yml` file

```
cp config.sample.yml config.yml
```

Adjust all required settings in the `config.yml` file before running. Optional settings can also be adjusted later.

## Prerequsistes

### Matrix
- You need a Matrix account on [Matrix.org](https://matrix.org) (or any other server) for the bot user. 
- By default, anyone that knows the name of your bot can invite it to rooms or chat with it.

### OpenAI / ChatGPT
- You need to have an account at [openai.com](https://openai.com/). Please note that the usage of the ChatGPT-API is not free.
- Create a [API Key](https://platform.openai.com/account/api-keys). Then, set `OPENAI_API_KEY` in your `.env` file
- invite the Bot in an new created room
- 

# Run

There are multiple ways to run this bot. The easiest way is to run it within docker.

## with Docker Compose

This is the recommended way to run this project. It will use the latest stable release.

```
docker-copose up -d
```

Note: Without -it flags in the command above you won't be able to stop the container using Ctrl-C

Note: In order to see the output of your console you need to run `docker logs matrix-chatgpt-bot`

## without Docker

**Important**: It is strongly recommended to run this package under Docker to not need to install various dependencies manually.
Nevertheless, you can also run it by using the package manager yarn (get it via `apt install -y yarn`). You might also need to have a newer version of Node.js and other missing packages. 

- `python -m venv .venv`
- `source .venv/bin/activate`
- `pip3 install -r source/requirements.txt`
- `python3 source/bot.py`
