# AstroPiCustoms
---
#### Raspberry Pi OS Setup:
* Choose "Raspberry Pi OS with desktop" 
    https://www.raspberrypi.com/software/
* Follow default install and set the following:
    * Configure Wifi
    * Add Host name, as description of the telescope (ie: "astropidob12")
    * Enable SSH
    * Disable Serial Console 
    * Enable Serial Port
---
#### AstorPiCustoms Install:
* **_AstorPiCustoms should be installed on a fresh install of Raspberry OS_**
* SSH into the fresh install and run the following command from a terminal: 
    * `wget -O - https://raw.githubusercontent.com/troysworks/AstroPiCustoms/main/setup.sh | bash`
* Update the `config.json` (`~/AstroPiCustoms/config.json`) file to include your relevant information:
    ```javascript
      {
          "latitude": 39.89169776,
          "longitude": -104.918,
          "sea_level": 1636,
          "ra_or_az_pulse_per_deg": 0.000624,
          "dec_or_alt_pulse_per_deg": 0.00073,
          "mount_select": 2
      }
* The install adds a service to start on boot-up. Restart now to complete installation.
---
#### Start and Stop AstroPiCustoms Service
* To manually Start service
    * `sudo systemctl start astropicustoms`  
* To manually Stop service (service will resume on restart)
    * `sudo systemctl stop astropicustoms`
---
#### Run AstroPiCustoms Web Interface
* `http://<<yourhostname>>/` on your PC or Phone
    * Example: http://astropidob12/
---

