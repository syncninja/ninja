basedir=`dirname "$0"`
basedir=${basedir}/../lib/node_modules/syncninja/
mkdir -p ~/.ninja

key="$1"
case $key in
    login)
    node ${basedir}/login.js
    ;;

    *)    # unknown option (e.g. start recording)
        node ${basedir}/nodeRecorder/record.js ~/.ninja/output_file.json && python3 ${basedir}/nodeParser/parser.py ~/.ninja/output_file.json
    ;;
esac