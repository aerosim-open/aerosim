import argparse
import json

from mcap.reader import make_reader

def _mcap_to_json(input_filename, output_filename):

    with open(input_filename, "rb") as f:
        reader = make_reader(f)
    
        messages = []
        for _, channel, msg in reader.iter_messages():
            messages.append({
                "topic": channel.topic,
                "log_time": msg.log_time,
                # Assume data is stored as json
                "data": json.loads(msg.data.decode("utf-8")),
            })
    
    with open(output_filename, "w") as json_file:
        json.dump(messages, json_file, indent=4)

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='MCAP to JSON')
    argparser.add_argument('-i', '--input', default='', required=True, help='mcap file to be converted')
    argparser.add_argument('-o', '--output', default='output.json', help='output json file')

    args = argparser.parse_args()

    _mcap_to_json(args.input, args.output)
