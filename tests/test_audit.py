import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from fine_tuning_claim_audit.audit import audit, evidence, main, matches, FINETUNING, NOFINETUNING, GENERIC_NAMES

class AuditTests(unittest.TestCase):
    def test_phrase_oracle(self):
        self.assertEqual(list(FINETUNING), ['fine-tuning', 'fine tuning', 'fine-tuned', 'fine tuned', 'fine-tune', 'fine tune', 'fine-tunes', 'fine tunes', 'fine-tuning support', 'fine tuning support', 'supports fine-tuning', 'supports fine tuning', 'fine-tuned model', 'fine-tuned models', 'fine-tuning pipeline', 'fine-tuning capability', 'fine-tuning feature', 'fine-tuning tool', 'fine-tuning framework', 'fine-tuning library', 'fine-tuning api', 'fine-tuning process', 'fine-tuning step', 'fine-tuning engine', 'fine-tuning system', 'fine-tuning module', 'fine-tuning function', 'fine-tuning functionality', 'fine-tuning workflow', 'fine-tuning training', 'fine-tuning method', 'fine-tuning approach', 'fine-tuning service', 'fine-tuning results', 'fine-tuning performance', 'fine-tune a model', 'fine-tune the model', 'fine-tunes the model', 'fine-tuned weights', 'fine-tuned checkpoint', 'fine-tuned checkpoints', 'model fine-tuning', 'model fine tuning', 'fine-tuning mode', 'fine-tuning task', 'fine-tuning tasks', 'fine-tuning algorithm', 'fine-tuning algorithms', 'fine-tuning configuration', 'fine-tuning script'])
        self.assertEqual(list(NOFINETUNING), ['does not fine-tune', 'do not fine-tune', "doesn't fine-tune", "don't fine-tune", 'no fine-tuning', 'without fine-tuning', 'never fine-tunes', 'does not support fine-tuning', 'fine-tuning not supported', 'fine-tuning unsupported', 'no fine-tuning support', 'lacks fine-tuning', 'missing fine-tuning', 'fine-tuning disabled', 'no fine-tuned model', 'without fine-tuning support', 'does not provide fine-tuning', 'no automatic fine-tuning', 'fine-tuning not available', 'no fine-tuning capability', 'does not fine-tune the model', 'without a fine-tuned model', 'does not perform fine-tuning', 'never performs fine-tuning'])

    def test_generic_oracle(self):
        self.assertEqual(list(GENERIC_NAMES), ['fine_tune', 'finetune', 'fine_tune_model', 'finetune_model', 'run_fine_tuning', 'run_finetuning', 'perform_fine_tuning', 'perform_finetuning', 'start_fine_tuning', 'start_finetuning', 'do_fine_tuning', 'do_finetuning', 'execute_fine_tuning', 'apply_fine_tuning', 'get_fine_tuned_model', 'create_fine_tuned_model', 'fine_tune_llm', 'finetune_llm', 'fine_tune_transformer', 'fine_tune_weights', 'train_fine_tuned_model', 'fine_tuning_train', 'tune_with_fine_tuning', 'setup_fine_tuning'])

    def fixture(self, readme='', code='', extra=None, flags=()):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'README.md').write_text(readme)
            (root/'app.py').write_text(code)
            for name, text in (extra or {}).items():
                p = root/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                status = main(['audit', str(root)] + list(flags))
            return status, out.getvalue()

    def test_inventory_matching(self):
        for phrase in FINETUNING:
            with self.subTest(phrase=phrase):
                self.assertEqual(matches(phrase, FINETUNING)[0], [phrase])
        for phrase in NOFINETUNING:
            with self.subTest(phrase=phrase):
                denials, rest = matches(phrase, NOFINETUNING)
                self.assertEqual(denials, [phrase])
                self.assertEqual(matches(rest, FINETUNING)[0], [])
        self.assertEqual(matches('fine-tuning support', FINETUNING)[0], ['fine-tuning support'])

    def test_generics(self):
        for name in GENERIC_NAMES:
            for code in ('x.'+name+'()', 'from unknown import '+name+' as run; run()', 'from unknown import '+name+'; '+name+'()'):
                with self.subTest(code=code): self.assertTrue(evidence(code))

    def test_matching(self):
        self.assertEqual(matches('fine-tuning', FINETUNING)[0], ['fine-tuning'])
        self.assertEqual(self.fixture('does not fine-tune')[0], 0)
        self.assertEqual(self.fixture('FINE-TUNING')[0], 2)
        self.assertEqual(self.fixture('```text\nfine-tuning\n```')[0], 0)
        self.assertEqual(self.fixture('`fine-tuning`')[0], 2)
        self.assertEqual(matches('fine_tuning', FINETUNING)[0], [])

    def test_cli_good(self):
        self.assertEqual(self.fixture('fine-tuning', 'x.fine_tune()'), (0, 'PASS\n'))

    def test_cli_bad(self):
        status, out = self.fixture('fine-tuning')
        self.assertEqual(status, 2)
        self.assertIn('HIGH documented-fine-tuning-claim-false', out)

    def test_cli_test_only(self):
        extra = {'tests/sample.md': 'fine-tuning'}
        status, out = self.fixture(extra=extra)
        self.assertEqual(status, 0)
        self.assertIn('MEDIUM', out)
        self.assertEqual(self.fixture(extra=extra, flags=['--fail-on', 'medium'])[0], 2)

    def test_cli_denial(self):
        status, out = self.fixture('no fine-tuning', 'x.fine_tune()')
        self.assertEqual(status, 2)
        self.assertIn('HIGH documented-no-fine-tuning-claim-false', out)

    def test_cli_no_claim(self):
        self.assertEqual(self.fixture('A useful tool.'), (0, 'PASS\n'))

    def test_cli_json(self):
        status, out = self.fixture('fine-tuning', flags=['--json'])
        f = json.loads(out)[0]
        self.assertEqual(status, 2)
        self.assertEqual(f['verdict'], 'FAIL')
        self.assertTrue(f['message'])

    def test_cli_ignore(self):
        self.assertEqual(self.fixture(extra={'docs/claim.md': 'fine-tuning'}, flags=['--ignore', 'docs/'])[0], 0)

    def test_cli_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            main(['--version'])
        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), '0.1.0')

    def test_readme(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(self.fixture((root/'README.md').read_text()), (0, 'PASS\n'))

    def test_io_and_usage(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['audit', '/nonexistent-r142-directory']), 1)
            with self.assertRaises(SystemExit) as cm: main(['audit', '--unknown'])
        self.assertEqual(cm.exception.code, 1)

    def test_virtualenv_excluded(self):
        status, out = self.fixture('fine-tuning', extra={
            'custom-env/pyvenv.cfg': 'home = /usr/bin',
            'custom-env/lib/model.py': 'x.fine_tune()',
        })
        self.assertEqual(status, 2)

    def test_verbose(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(self.fixture(flags=['--verbose'])[0], 0)
        self.assertIn('scope:', err.getvalue())

    def test_positive_pairs(self):
        cases = [
            'from transformers import Trainer; t=Trainer(); t.train()',
            'import transformers as tf; tf.Trainer().train()',
            'from transformers import Trainer as T; T().train()',
            'from transformers import Seq2SeqTrainer; Seq2SeqTrainer().train()',
            'import transformers as tf; t=tf.Seq2SeqTrainer(); t.train()',
            'from trl import SFTTrainer; t=SFTTrainer(); t.train()',
            'import trl as tr; tr.SFTTrainer().train()',
            'from peft import LoraConfig, get_peft_model; c=LoraConfig(); get_peft_model(model,c)',
            'import peft as p; p.get_peft_model(model,p.LoraConfig())',
            'from peft import LoraConfig as L, get_peft_model as G; c=L(); d=c; G(model,peft_config=d)',
            'client.fine_tuning.jobs.create(model="x")',
            'openai.fine_tuning.jobs.create()',
            'from transformers import Trainer; t=Trainer(); u=t; u.train()',
        ]
        for code in cases:
            with self.subTest(code=code): self.assertTrue(evidence(code))

    def test_rejections(self):
        cases = [
            'import transformers, peft, trl, openai',
            'from transformers import AutoModel; m=AutoModel.from_pretrained("x"); m.generate(); m.predict(); m()',
            'import optuna; study=optuna.create_study(); study.optimize(objective)',
            'import ray; ray.tune.run(train)',
            'from sklearn.model_selection import GridSearchCV; m=GridSearchCV(); m.fit(x,y)',
            'from sklearn.model_selection import RandomizedSearchCV; m=RandomizedSearchCV(); m.fit(x,y)',
            'from transformers import Trainer; t=Trainer()',
            'from transformers import Seq2SeqTrainer; Seq2SeqTrainer()',
            'from trl import SFTTrainer; SFTTrainer()',
            'from peft import LoraConfig; LoraConfig()',
            'from peft import get_peft_model; get_peft_model(m,config)',
            'from peft import LoraConfig,get_peft_model; c=LoraConfig(); get_peft_model(m,other)',
            'client.fine_tuning.jobs.list()',
            'client.fine_tuning.jobs.retrieve(id)',
            'client.fine_tuning.jobs.cancel(id)',
            'client.fine_tuning',
            'client.jobs.fine_tuning.create()',
            'client.fine_tuning.create()',
            '"fine-tuning fine-tune" # fine-tuning',
            '\"\"\"fine-tuning\"\"\"',
            'from x import fine_tune; fine_tune',
            'fine_tune()',
            'import fine_tune; fine_tune()',
            'import x.fine_tune as run; run()',
            'import subprocess; subprocess.run(["fine-tune", "model"])',
            'from transformers import Trainer; t=Trainer(); other.train()',
            'from unrelated import Trainer; Trainer().train()',
            'from unrelated import LoraConfig,get_peft_model; get_peft_model(m,LoraConfig())',
            'invalid python!',
        ]
        for code in cases:
            with self.subTest(code=code): self.assertFalse(evidence(code))

    def test_shadowing(self):
        cases = [
            'from x import fine_tune\ndef fine_tune(): pass\nfine_tune()',
            'from transformers import Trainer\nclass Trainer: pass\nTrainer().train()',
            'import transformers as tf\ndef tf(): pass\ntf.Trainer().train()',
            'from trl import SFTTrainer\nclass SFTTrainer: pass\nSFTTrainer().train()',
            'from peft import LoraConfig,get_peft_model\nclass LoraConfig: pass\nget_peft_model(m,LoraConfig())',
            'from peft import LoraConfig,get_peft_model\ndef get_peft_model(*a): pass\nget_peft_model(m,LoraConfig())',
            'from x import fine_tune as run\ndef run(): pass\nrun()',
            'class client: pass\nclient.fine_tuning.jobs.create()',
        ]
        for code in cases:
            with self.subTest(code=code): self.assertFalse(evidence(code))

    def test_split_modules(self):
        for code, other in [
            ('from transformers import Trainer; t=Trainer()', 't.train()'),
            ('from trl import SFTTrainer; t=SFTTrainer()', 't.train()'),
            ('from peft import LoraConfig; c=LoraConfig()', 'from peft import get_peft_model; get_peft_model(m,c)'),
        ]:
            with self.subTest(code=code):
                self.assertEqual(self.fixture('fine-tuning',code,{'other.py':other})[0],2)

    def test_collision(self):
        self.assertEqual(matches('fine-tuner', FINETUNING)[0], ['fine-tune'])
        self.assertEqual(self.fixture('fine-tuner')[0], 2)

    def test_docs_scope(self):
        self.assertEqual(self.fixture(extra={'docs/nested/a.md':'fine-tuning'})[0],2)
        self.assertEqual(self.fixture(extra={'other.md':'fine-tuning'})[0],0)

if __name__ == '__main__':
    unittest.main()
