from pprint import pprint
import pyte
import sys
import re
import copy
import json
import string
import publisher


prompt_prefix = "◉ "
prompt_suffix = "◉ "
pattern = prompt_prefix + ".*?" + prompt_suffix


def evaluate_term(content):
    # The size is big in order to fit any output
    # Check the amount of lines in the content (min 10 lines)
    line_num = content.count('\n') + 10
    screen = pyte.Screen(400, line_num)
    stream = pyte.Stream(screen)
    stream.feed(content)
    return screen.display


def eval_terminal_print_output(input):
    return ('\n'.join([line.rstrip() for line in evaluate_term(input)])).rstrip('\n')


def eval_terminal_print_input(input, is_commandline=True):
    evaluated_string = ''.join(evaluate_term(input))
    # Removing the prompt
    prompt_ending = 0
    prompt_string = re.search(pattern, evaluated_string)

    # Assuming that the prompt must exist, otherwise something strange happened
    if is_commandline and prompt_string:
        prompt_ending = prompt_string.span()[1]

    # Strip the result after cleaning the prompt
    evaluated_string = evaluated_string[prompt_ending:].strip()

    return evaluated_string


def aggregate_io_sequence(input):

    # Aggregated output
    output = []

    buffer = ''

    i = 0
    while i < len(input):
        buffer = input[i]['content']
        mode = input[i]['type']

        while (i + 1) < len(input) and mode == input[i+1]['type']:
            buffer += input[i + 1]['content']
            i += 1

        output.append({"type": mode, "content": buffer,
                      "time": input[i]['time']})

        i += 1

    return output


def aggregate_user_input(input, is_commandline=True):

    # Aggregated output
    command = ''

    if is_commandline:
        # Assuming the first output is the prompt, if not we have a problem
        prompt_string = re.findall(pattern, input[0]['content'])
        if not prompt_string:
            raise RuntimeError('The Prompt line  is missing')
        # Taking the last prompt command in case there are many in the bundel
        command += prompt_string[-1]

    i = 0
    # Assuming the last input is an prompt output
    while i < len(input) - 1:

        if input[i]['type'] == 'input':
            current_input = input[i]['content']
            current_output = input[i + 1]['content']
            # Check for completion
            # Stopping only in case the input and the output has \r in order to avoid
            # in prompt games to be displayed (like autocompletion)
            if '\r' in current_output and '\r' in current_input:
                breakline_pos = current_output.find('\r')
                # Adding all the non-printable chars to the string
                next_printable = breakline_pos
                while next_printable < len(current_output) and not current_output[next_printable].isprintable():
                    # Check if current char is <esc> char, in that case add two chars after (indicate the escape code)
                    # see also: https://en.wikipedia.org/wiki/ANSI_escape_code
                    # TODO: Add a regex that indicates if there is a number we need to parse '\u001b[49C'
                    if next_printable + 2 < len(current_output) and current_output[next_printable] == '\u001b':
                        next_printable += 2
                    next_printable += 1
                command += current_output[:next_printable]
                # Increasing to indicate next command
                i += 1
                break
            command += current_output

        i += 1

    command = eval_terminal_print_input(command, is_commandline)
    return (command, i)


def split_commands(json_input):
    # Split the whole input into commands
    commands = []

    # Clear begginging pre prompt inputs
    commands_beggining = 0
    while not re.search(pattern, json_input[commands_beggining]['content']) and commands_beggining < len(json_input):
        commands_beggining += 1
    if commands_beggining == len(json_input):
        return commands
    json_input = json_input[commands_beggining:]

    # Clear the prefix before the prompt in the first time
    first_command_beggining = re.search(
        pattern, json_input[0]['content']).span()[0]
    json_input[0]['content'] = json_input[0]['content'][first_command_beggining:]

    # split json
    is_in_command = False
    command_inputs = [json_input[0]]
    # To avoid first time flush
    is_first_time = True
    # Starting from the second
    i = 1
    while i < len(json_input):
        if re.search(pattern, json_input[i]['content']):
            # Cut the input to the end of previous command and new command
            partial_input = copy.deepcopy(json_input[i])
            prompt_pos = re.search(pattern, partial_input['content']).span()[0]
            if prompt_pos > 0:
                partial_input['content'] = partial_input['content'][:prompt_pos]
                command_inputs.append(partial_input)
                json_input[i]['content'] = json_input[i]['content'][prompt_pos:]

            commands.append(command_inputs)
            command_inputs = []

        command_inputs.append(json_input[i])
        i += 1

    commands.append(command_inputs)
    return commands


def parse_process_io(json_input):

    io_result = []

    i = 0
    while i < len(json_input):
        if json_input[i]['type'] == 'input':
            input_buffer, output_offset = aggregate_user_input(
                json_input[i:], False)
            i += output_offset
            io_result.append({'input': input_buffer})
            if not i < len(json_input):
                break

        # Current input may change to output because of previous parsing
        if json_input[i]['type'] == 'output':
            # Cleaning the newline in the begining (and the user input)
            output_buffer = json_input[i]['content']
            reg_position = re.search('\r\n', output_buffer)
            if reg_position:
                output_buffer = output_buffer[reg_position.span()[1]:]
            io_result.append(
                {'output': eval_terminal_print_output(output_buffer)})

        i += 1

    return io_result


def parse_raw_command(json_command_input):
    # Parse each command and split it to command input and result

    # Find the command header and clean in
    bash_command, process_start = aggregate_user_input(
        json_command_input, True)
    bash_command = bash_command.strip()

    # Check if the command is a comment
    if bash_command.startswith('#'):
        return {'type': 'comment', 'comment': bash_command}

    process_io = []
    if process_start < len(json_command_input):
        process_io = parse_process_io(json_command_input[process_start:])

    # Check whether the command has a comment
    if ' #' in bash_command:
        comment_start = bash_command.find(' #')
        complete_command = {'type': 'command',
                            'comment': bash_command[comment_start+1:],
                            'command': bash_command[:comment_start],
                            'process_io': process_io}
    else:
        complete_command = {'type': 'command',
                            'command': bash_command,
                            'process_io': process_io}

    return complete_command


def main():
    if len(sys.argv) < 2:
        print(" Usage: python parser.py file.json")
        return

    # Read the recording json file
    data = open(sys.argv[1]).read()
    x = json.loads(data)
    x = aggregate_io_sequence(x)

    # Split the file into commands and the io of the process
    splitted_commands = split_commands(x)

    # Aggregate the commands
    splitted_commands = [parse_raw_command(
        command) for command in splitted_commands]
    publisher.publish(splitted_commands)


if __name__ == '__main__':
    main()
