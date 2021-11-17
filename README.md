##### Setup

On the data server, run `$bash scripts/server/setup.sh`\
On any raspberry pi, run `$bash scripts/raspi/setup.sh` and follow the instructions given.

All configuration options can be modified in config/server_config.json and config/raspi_config.json

##### Running the application

On the pi, run `$bash scripts/raspi/run.sh`.

For the server, make sure that the port you wish to use is open on the network the server is connected to.

Start the server by running `$bash scripts/server/run_all.sh`

Use a browser to navigate to your domain name.
