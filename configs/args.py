import sys
import argparse
import yaml
from configs import parser as _parser
import distutils

args = None


def parse_arguments():
    parser = argparse.ArgumentParser(description="Speech decoding by MetaAI reimplementation")

    parser.add_argument("--config", default=None, help="Config file to use (see configs dir)")
    parser.add_argument("--name", type=str, default="test")
    parser.add_argument("--batch-size", default=64)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--lr-gamma", type=float, default=0.97, help="Decay rate for exponential lr scheduler")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--num-subjects", default=27)
    parser.add_argument("--D1", type=int, default=270, help="D_1 in the paper")
    parser.add_argument("--D2", type=int, default=320)
    parser.add_argument("--F", type=int, default=512, help="Embedding dimension for both speech and M/EEG")
    parser.add_argument("--K", type=int, default=32, help="Number of harmonics in fourier space for spatial attention")
    parser.add_argument("--wandb", action='store_true', help="Whether to log to wandb")
    parser.add_argument("--force_recompute", action='store_true', help="Recompute EEG even if exists")
    parser.add_argument("--reproducible", action='store_true', help="Seed everything")

    args = parser.parse_args()

    if len(sys.argv) > 1:
        get_config(args)
    return args


def get_config(args):
    # get commands from command line
    override_args = _parser.argv_to_vars(sys.argv)

    # load yaml file
    yaml_txt = open(args.config).read()

    # override args
    loaded_yaml = yaml.load(yaml_txt, Loader=yaml.FullLoader)
    for v in override_args:
        loaded_yaml[v] = getattr(args, v)

    print(f"=> Reading YAML config from {args.config}")
    args.__dict__.update(loaded_yaml)


def run_args():
    global args
    if args is None:
        args = parse_arguments()


run_args()
