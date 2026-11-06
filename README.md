# Documentation claim auditor

An offline, deterministic, standard-library-only auditor for documentation claims
about weight updates and adapting a checkpoint. Requires Python 3.9 or later.
The auditor uses no LLM, network, telemetry, or model execution and writes no files.

## Usage

```sh
python3 -m pip install .
fine-tuning-claim-audit audit .
python3 -m fine_tuning_claim_audit audit . --json
fine-tuning-claim-audit audit . --verbose --ignore vendor/ --ignore examples/
fine-tuning-claim-audit audit . --fail-on medium
fine-tuning-claim-audit --version
fine-tuning-claim-audit --help
```

The repository defaults to the current directory. Exit status is 0 when no
finding reaches the threshold, 2 when one does, and 1 for usage or IO errors.
The default threshold is high. JSON output is a list of findings with id,
severity, path, verdict, message, and matched phrases. Verbose scan scope and
per-file decisions go to standard error. Ignore prefixes are repeatable and
match the start of repository-relative paths.

## Scope and rules

Scans the root README and Markdown below docs. Claim fixtures under a tests
directory receive medium severity. Python evidence is searched throughout the
repository, excluding version control, bytecode caches, virtual environments,
and build output. Each evidence route must be complete in one module.
Imported aliases, simple assigned aliases, and chained calls are recognized.
Local function and class definitions shadow imported route names in that module.
Unparseable modules supply no evidence.

Fenced code is excluded; inline code counts as prose. Matching uses exact,
case-insensitive substrings without stemming or hyphen normalization. Denial
spans are removed before checking positive claims. Longest-first matching
blanks spans so each occurrence matches once under its longest phrase. The
substring rule can also match within a longer word, as in this collision:

```text
fine-tune matches inside fine-tuner
```

A claim without evidence is high severity; a denial contradicted by evidence
is high severity. A denial without evidence passes. Test-only claims without
evidence receive medium severity. Finding identifiers are:

```text
documented-fine-tuning-claim-false
documented-no-fine-tuning-claim-false
```

## Differentiation

These neighboring tools check generating speech, cloning a voice from a
reference clip, and transcribing speech, respectively:

```text
text-to-speech-claim-audit
voice-cloning-claim-audit
speech-recognition-claim-audit
```

This auditor checks claims about weight updates. Those neighboring capabilities
alone do not supply evidence for the checked feature.

## Evidence and limitations

Static pattern matching is not semantic judgement. Exact phrases miss
restatements. Generic calls on unrelated objects count because the method name
is shared, including this example:

```python
unrelated.fine_tune()
```

A generic attribute call on any base counts; a bare call needs a matching
from-import, including an alias. An unbound bare call is rejected.

The following trainer constructions require a call on the constructed instance,
either assigned or chained, in the same module:

```text
transformers.Trainer + .train()
transformers.Seq2SeqTrainer + .train()
trl.SFTTrainer + .train()
```

These patterns cannot distinguish adapting a checkpoint from training from
scratch or pre-training: all three use the same calls. The auditor checks that
the operation is invoked, not what data it trained on.

The following pair counts on config construction plus a receiving call, using
an assigned config value or an inline construction:

```python
from peft import LoraConfig, get_peft_model
config = LoraConfig()
model = get_peft_model(model, config)
```

This shows use of the checked capability, not that resulting weights are any
good. It does not require a later training call.

The following job creation chain is trusted on its attribute names alone,
on any base, without a network call or validation of the client type:

```python
client.fine_tuning.jobs.create(...)
```

Listing, retrieving, or cancelling jobs does not count. Bare imports, setup
alone, references, strings, comments, docstrings, subprocess commands, inference,
and hyperparameter search alone supply no evidence. Evidence split across
modules does not count. Control flow and runtime types are not evaluated, and
this tool cannot assess model quality or guarantee correctness for every input.

## Development

```sh
python3 -m unittest discover
python3 -m build
```

Distributed under the MIT license.
