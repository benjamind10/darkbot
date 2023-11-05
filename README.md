# DarkBot

DarkBot is a versatile Discord bot designed to enhance server interaction and management. Whether you're looking to moderate your server, play music, or fetch useful information, DarkBot has got you covered.

## Features
- Moderation: Keep your server in check with a variety of moderation features.
- Music Playback: Enrich your server experience with music playback capabilities.
- Information Retrieval: Fetch useful information directly through Discord.
- And much more awaiting to be explored!

## Getting Started

These instructions will help you get a copy of DarkBot up and running on your machine.

### Prerequisites

- Ensure you have [Docker](https://www.docker.com/get-started) installed on your machine.

### Setup

1. **Clone the Repository:**
    ```bash
    git clone https://github.com/benjamind10/darkbot.git
    cd darkbot
    ```

2. **Environment Configuration:**
   - You'll need to set up two `.env` files: one in the project root directory and another in the `bot` folder.
   - Examples are provided in each respective folder to guide you through setting up your `.env` files correctly.

3. **Docker-Compose:**
   - With Docker installed and the `.env` files set up, you can start the bot using the following command:
     ```bash
     docker-compose up -d
     ```
4. **Logging Setup:**
    - DarkBot utilizes logging to help keep track of events and potentially troubleshoot issues. To set up logging:
    - Create a `logs` folder in the project root directory:
   ```bash
     mkdir logs
     cd logs
     touch information.log owner.log music.log moderation.log
    ```

Now, DarkBot should be up and running on your machine, ready to be invited to your server!

## Contributing

Feel free to fork the project, open a PR, or submit issues if you have any suggestions or find bugs.

## Contact

- Discord: Shiva187#4664
- Email: benjamind10@pm.me

Explore, enjoy, and contribute to the development of DarkBot!

