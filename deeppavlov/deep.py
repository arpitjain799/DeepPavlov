"""
Copyright 2017 Neural Networks and Deep Learning lab, MIPT

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
from pathlib import Path
import sys
import os

p = (Path(__file__) / ".." / "..").resolve()
sys.path.append(str(p))

from deeppavlov.core.commands.train import train_evaluate_model_from_config
from deeppavlov.pipeline_manager.pipeline_manager_parallel import PipelineManager
from deeppavlov.core.commands.infer import interact_model, predict_on_stream
from deeppavlov.core.common.cross_validation import calc_cv_score
from deeppavlov.core.common.log import get_logger
from deeppavlov.download import deep_download
from utils.telegram_utils.telegram_ui import interact_model_by_telegram
from utils.server_utils.server import start_model_server
from utils.ms_bot_framework_utils.server import start_bot_framework_server
from utils.pip_wrapper import install_from_config


log = get_logger(__name__)

parser = argparse.ArgumentParser()

parser.add_argument("mode", help="select a mode, train or interact", type=str,
                    choices={'train', 'evaluate', 'interact', 'predict', 'interactbot', 'riseapi', 'download',
                             'install', 'interactmsbot', 'enumerate', 'crossval'})
parser.add_argument("config_path", help="path to a pipeline json config", type=str)
parser.add_argument("-e", "--exp_name", help="name of experiment", type=str)
parser.add_argument("-b", "--batch-size", dest="batch_size", default=1, help="inference batch size", type=int)
parser.add_argument("-f", "--input-file", dest="file_path", default=None, help="Path to the input file", type=str)
parser.add_argument("-d", "--download", action="store_true", help="download model components")

parser.add_argument("--folds", dest='folds', help="number of folds", type=int, default=5)

parser.add_argument("-t", "--token", help="telegram bot token", type=str)
parser.add_argument("-i", "--ms-id", help="microsoft bot framework app id", type=str)
parser.add_argument("-s", "--ms-secret", help="microsoft bot framework app secret", type=str)

parser.add_argument("--multi-instance", action="store_true", help="allow rising of several instances of the model")
parser.add_argument("--stateful", action="store_true", help="interact with a stateful model")
parser.add_argument("--use-history", action="store_true", help="feed model with an interaction history")

parser.add_argument("-r", "--root", dest="root", default='./download/experiments',
                    help="folder where you will save the results and control points", type=str)
parser.add_argument("-p", "--plot", dest="plot", default=False,
                    help="If true it is plot a histograms with results", type=bool)
parser.add_argument("-cv", "--cross-val", dest="cross_val", default=False, help="cross validation", type=bool)
parser.add_argument("-sn", "--sample-num", dest="sample_num", default=1,
                    help="Number of generated samples if you use random search", type=int)
parser.add_argument("-tm", "--target-metric", dest="target_metric", default=None,
                    help="If you use more than one metric then target metric will be used"
                         " for results sortings", type=str)
parser.add_argument("-sb", "--save-best", dest="save_best", default=True,
                    help="If true then algorithm saved only one best pipeline checkpoint for each dataset", type=bool)


def find_config(pipeline_config_path: str):
    if not Path(pipeline_config_path).is_file():
        configs = [c for c in Path(__file__).parent.glob(f'configs/**/{pipeline_config_path}.json')
                   if str(c.with_suffix('')).endswith(pipeline_config_path)]  # a simple way to not allow * and ?
        if configs:
            log.info(f"Interpreting '{pipeline_config_path}' as '{configs[0]}'")
            pipeline_config_path = str(configs[0])
    return pipeline_config_path


def main():
    args = parser.parse_args()
    pipeline_config_path = find_config(args.config_path)

    if args.download or args.mode == 'download':
        deep_download(['-c', pipeline_config_path])
    token = args.token or os.getenv('TELEGRAM_TOKEN')

    ms_id = args.ms_id or os.getenv('MS_APP_ID')
    ms_secret = args.ms_secret or os.getenv('MS_APP_SECRET')

    multi_instance = args.multi_instance
    stateful = args.stateful
    use_history = args.use_history

    if args.mode == 'train':
        train_evaluate_model_from_config(pipeline_config_path)
    elif args.mode == 'evaluate':
        train_evaluate_model_from_config(pipeline_config_path, to_train=False, to_validate=False)
    elif args.mode == 'interact':
        interact_model(pipeline_config_path)
    elif args.mode == 'interactbot':
        if not token:
            log.error('Token required: initiate -t param or TELEGRAM_BOT env var with Telegram bot token')
        else:
            interact_model_by_telegram(pipeline_config_path, token)
    elif args.mode == 'interactmsbot':
        if not ms_id:
            log.error('Microsoft Bot Framework app id required: initiate -i param '
                      'or MS_APP_ID env var with Microsoft app id')
        elif not ms_secret:
            log.error('Microsoft Bot Framework app secret required: initiate -s param '
                      'or MS_APP_SECRET env var with Microsoft app secret')
        else:
            start_bot_framework_server(model_config_path=pipeline_config_path,
                                       app_id=ms_id,
                                       app_secret=ms_secret,
                                       multi_instance=multi_instance,
                                       stateful=stateful,
                                       use_history=use_history)
    elif args.mode == 'riseapi':
        start_model_server(pipeline_config_path)
    elif args.mode == 'predict':
        predict_on_stream(pipeline_config_path, args.batch_size, args.file_path)
    elif args.mode == 'enumerate':
        manager = PipelineManager(config_path=pipeline_config_path, exp_name=args.exp_name, root=args.root,
                                  cross_val=args.cross_val, k_fold=args.folds, sample_num=args.sample_num,
                                  target_metric=args.target_metric, plot=args.plot, save_best=args.save_best)
        manager.run()
    elif args.mode == 'install':
        install_from_config(pipeline_config_path)
    elif args.mode == 'crossval':
        if args.folds < 2:
            log.error('Minimum number of Folds is 2')
        else:
            n_folds = args.folds
            calc_cv_score(pipeline_config_path, n_folds=n_folds, is_loo=False)


if __name__ == "__main__":
    main()
