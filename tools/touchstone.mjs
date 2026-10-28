#!/usr/bin/env node
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {run} from '../_build/js/release/build/cmd/bridge/bridge.js';

const usage = `Usage: node tools/touchstone.mjs COMMAND INPUT [OPTIONS-JSON] [OUTPUT]
Commands: inspect validate dump normalize legacy convert renormalize select
          interpolate cascade deembed diagnostics metrics delay band-check band-csv ripple-check
          rf-convert mixed single modal modal-metrics terminate terminate-file stability noise transducer-gain
          transducer-gain-impedance
          gain-check gain-csv
          gain-record gain-review
Legacy INPUT.sNp supplies its port count; otherwise OPTIONS needs "ports".
Options: parameter, reference_ohms, selection, frequency_hz, input/output (ports),
         tolerance, format, unit, left_file/right_file (fixtures).
Band options: limits (1..256 rules), max_details (global issue budget).
Transducer gain: source/load as [Gamma real,imag], default matched [0,0].
Impedance gain: required source_ohms/load_ohms as [real,imag] in ohm.
Terminate file: terminations as [original port,re,im], impedance false Gamma/true ohm;
                writes single-ended S Touchstone with information; noisy input is rejected.
Gain check: start_hz/end_hz, minimum_db/maximum_db, terminal_mode gamma/impedance.
Gain CSV: same query; every selected original sample with state and limit disposition.
Gain record: same query options, output a byte-bound receipt; exits 0/3/4.
Gain review: INPUT @RECEIPT [OUTPUT]; exits 0 reproduced, 5 mismatch, 2 error.
OPTIONS-JSON may be @path/to/options.json (ASCII, <=1 MB).
Band/gain-check exits: 0 sampled pass, 3 fail, 4 inconclusive; input/IO errors: 2.
Output files are created exclusively: existing files are never overwritten.
Reports print JSON; file transformations print Touchstone if OUTPUT is absent.`;

function read(file, maxBytes=64_000_000) {
  // Open before fstat to avoid path-swap races; bound allocation and reject
  // non-ASCII bytes instead of silently replacing them during UTF-8 decoding.
  const fd = fs.openSync(file, 'r');
  try {
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > maxBytes) throw new Error(`input must be a file <=${maxBytes} bytes`);
    const data = Buffer.alloc(stat.size + 1);
    let size = 0, count;
    while (size < data.length && (count = fs.readSync(fd, data, size, data.length-size, null))) size += count;
    if (size > stat.size) throw new Error('input grew while reading; retry a stable file');
    if (size < stat.size) throw new Error('input shrank while reading; retry a stable file');
    for (let i=0;i<size;i++) if (data[i]>127) throw new Error('Touchstone input must be ASCII');
    return data.subarray(0,size).toString('ascii');
  } finally { fs.closeSync(fd); }
}

function infer(file, options, key) {
  const match = /\.s(\d+)p$/i.exec(file);
  if (match && options[key] === undefined) options[key] = Number(match[1]);
}

function identity(text) {
  // Hash the very same validated ASCII string passed to the MoonBit bridge.
  return {actual_input_sha256:createHash('sha256').update(text,'ascii').digest('hex'),actual_input_bytes:Buffer.byteLength(text,'ascii')};
}

try {
  const args = process.argv.slice(2);
  if (args.length===1 && ['--help','-h'].includes(args[0])) { console.log(usage); }
  else {
    if (args.length<2 || args.length>4) throw new Error(usage);
    const [command, input, optionsArg='{}', output] = args;
    const optionsText=optionsArg.startsWith('@') ? read(optionsArg.slice(1),1_000_000) : optionsArg;
    if (optionsText.length>1_000_000) throw new Error('options too large');
    const options = JSON.parse(optionsText);
    if (!options || typeof options!=='object' || Array.isArray(options)) throw new Error('options must be an object');
    if (command==='gain-review') {
      const inputText=read(input);
      const result=JSON.parse(run(inputText,JSON.stringify({command:'gain-review',saved:options,...identity(inputText)}),'',''));
      const content=JSON.stringify(result,null,2)+'\n';
      if (output!==undefined) fs.writeFileSync(output,content,{encoding:'utf8',flag:'wx'});
      else process.stdout.write(content);
      process.exitCode=result.status==='reproduced' ? 0 : 5;
    } else {
    options.command = command==='gain-record' ? 'gain-check' : command;
    infer(input,options,'ports');
    let left='',right='';
    for (const side of ['left','right']) {
      // These commands have no fixture-file inputs; keep unknown options visible
      // to MoonBit validation instead of consuming and deleting them here.
      if (command==='transducer-gain' || command==='transducer-gain-impedance' || command==='gain-check' || command==='gain-csv' || command==='gain-record' || command==='terminate-file') continue;
      const file=options[`${side}_file`];
      if (file!==undefined) {
        if (typeof file!=='string') throw new Error(`${side}_file must be a path`);
        infer(file,options,`${side}_ports`);
        if (side==='left') left=read(file); else right=read(file);
        delete options[`${side}_file`];
      }
    }
    const inputText=read(input);
    const transported=command==='gain-record' ? {command:'gain-record',request:options,...identity(inputText)} : options;
    const result = JSON.parse(run(inputText,JSON.stringify(transported),left,right));
    const content = result && typeof result.text==='string' ? result.text : JSON.stringify(result,null,2)+'\n';
    if (output!==undefined) fs.writeFileSync(output,content,{encoding:'utf8',flag:'wx'});
    else process.stdout.write(content);
    if (command==='band-check' || command==='band-csv' || command==='ripple-check' || command==='gain-check' || command==='gain-csv' || command==='gain-record') {
      const status=command==='gain-record' ? result.result.status : result.status;
      process.exitCode = status==='fail' ? 3 : status==='inconclusive' ? 4 : 0;
    }
    }
  }
} catch (error) {
  console.error(`touchstone: ${error.message}`);
  process.exitCode = 2;
}
