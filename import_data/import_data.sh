# create an array with all the filer/dir inside ~/myDir
if psql -U ${user} -h ${psqlHost} -lqt | cut -d \| -f 1 | grep -qw ${database}
then
    # database exists
    echo '\033[94mNOTICE:\033[0m  Database \033[94m '${database}' \033[0m exists'
    #dropdb ${database} -U ${user}
    #createdb ${database} -U ${user}
else
    echo '\033[94mNOTICE:\033[0m  Database does not exist; creating \033[94m '${database}' \033[0m ...'
    ## this will help us create the database
	createdb ${database} -U ${user}
    psql -U ${user} -h ${psqlHost} ${database}<<OMG
    -- Create a group
    CREATE EXTENSION postgis;
OMG
    

fi


for f in "$search_dir"data/*.shp
do
    multi = ''
    out="$(basename -s .shp $f)"
    if [[ out == *"poly_data"* ]]; then
        echo "It's there!"
        multi = '-nlt PROMOTE_TO_MULTI'
    fi
    echo 'Importing... '$out
    
    ogr2ogr $multi -lco ENCODING=UTF-8 -lco GEOM_TYPE=geometry -lco GEOMETRY_NAME=geom -lco SPATIAL_INDEX=YES -lco LAUNDER=YES --config PG_USE_COPY YES -f PGDump ./$out.sql $f
    psql -U ${user} -d ${database} -f ./$out.sql
    rm ./$out.sql
done