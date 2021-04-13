const fs = require("fs");
const pty = require("node-pty");
const now = require("performance-now");

let records = [];
let buffer = "";

function onData(content) {
  process.stdout.write(content);

  records.push({
    type: "output",
    content: content,
    time: now(),
  });
}

function done() {
  process.stdin.setRawMode(false);
  process.stdin.pause();

  if (process.argv[2]) {
    fs.writeFileSync(process.argv[2], JSON.stringify(records));
  }
}

function fork_pty() {
  var bashType = process.env.SHELL;

  // Fork a new PTY
  var ptyProcess = pty.spawn(bashType, [], {
    name: "xterm-color",
    cols: process.stdout.columns,
    rows: process.stdout.rows,
    cwd: process.cwd(),
    env: process.env,
  });

  // The base64 trick is meant to make the seperator invisible (4peJIAo=='◉ ')
  ptyProcess.write("SEP=$(echo '4peJIAo=' | base64 --decode)\r");
  ptyProcess.write("export PS1=${SEP}${PS1}${SEP} && clear\r");

  // Capture Input
  const ptyWrite = ptyProcess.write.bind(ptyProcess);
  var onInput = (input) => {
    records.push({
      type: "input",
      content: input,
      time: now(),
    });

    ptyWrite(input);
  };

  // Input and output capturing and redirection
  process.stdin.on("data", onInput);
  process.stdin.setEncoding("utf8");
  process.stdin.setRawMode(true);
  process.stdin.resume();

  // Output recorder and printer
  ptyProcess.on("data", onData);

  ptyProcess.on("exit", function () {
    process.stdin.removeListener("data", onInput);
    done();
  });
}

if (require.main === module) {
  fork_pty();
}
