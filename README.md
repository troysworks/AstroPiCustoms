# AstroPiCustoms

#### Raspberry Pi OS Setup:
* Choose "Raspberry Pi OS with desktop" 
    https://www.raspberrypi.com/software/
* Follow default install and set the following:
    * Configure Wifi
    * Add Host name, as description of the telescope (ie: "astropidob12")
    * Enable SSH
    * Disable Serial Console 
    * Enable Serial Port

#### AstorPiCustoms Install:
* From a fresh OS install; run the following: 
    * `wget -O - https://raw.githubusercontent.com/troysworks/AstroPiCustoms/main/setup.sh | bash`
* Update the `config.json` file to include your relevant information:
    ```javascript
      {
          "latitude": 39.89169776,
          "longitude": -104.918,
          "sea_level": 1636,
          "ra_or_az_pulse_per_deg": 0.000624,
          "dec_or_alt_pulse_per_deg": 0.00073,
          "mount_select": 2
      }

#### Run AstroPiCustoms Web Interface
* The install adds a service to start on boot-up.
    * `http://<<yourhostname>>/` on your PC or Phone
