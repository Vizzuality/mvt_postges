# Service for VL
TODO  


The knowledge sorce came from this [medium article](https://medium.com/@renato.groffe/postgresql-pgadmin-4-docker-compose-montando-rapidamente-um-ambiente-para-uso-55a2ab230b89)  



## development
You will need to have installed [docker](https://docs.docker.com/install/) and [docker-compose](https://docs.docker.com/compose/install/); 

Don't forget to populate your `.env` file with the requirements

run `sh postgres-up.sh local` 

After pgadmin is up and running you can `http://0.0.0.0:16543/` to load into pg-admin.
In order to connect with the DB you should create server connection with network as the hostname, the port, username and password that you seted up on your `.env` file

For the service endpoint you should be able to access `http://0.0.0.0:5100/`
 
In order to populate the DB you will need to update the data as you need on the `/import_data`  folder. 
You will need to connect to the postgres container. To do so:
`docker exec -it geo-postgres /bin/bash`
`sh /data_import/import_data.sh`  
To check the folder: `cd /data_import`


## Tests
TODO

## Deployment
TODO