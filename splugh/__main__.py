#!/usr/bin/env python3

import shutil
import argparse
import sys
import os
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Union
import yaml
from marshmallow import ValidationError
import marshmallow.validate as mvalid
import marshmallow_dataclass
from jinja2 import Environment, PackageLoader, select_autoescape


ConfigListT = List['ConfigObjT']
ConfigDictT = Dict[str, 'ConfigObjT']
ConfigObjT = Union[ConfigDictT, ConfigListT, int, str, float]


@dataclass
class Page:
    title: str
    href: str
    shortcut: str = field(
        metadata={
            'validate': mvalid.Length(equal=1)
        }
    )


PageSchema = marshmallow_dataclass.class_schema(Page)()


@dataclass
class Config:
    title: str
    pages: List[Page]


ConfigSchema = marshmallow_dataclass.class_schema(Config)()


def parse_ext_to_format(ext: str):
    format_map = {
        'json': 'json',
        'yaml': 'yaml',
        'yml': 'yaml'
    }
    return format_map[ext]


ConfigParserT = Callable[[Any], Config]


def get_config_parser(file_format: str) -> ConfigParserT:
    def json_parser(file_contents: Any) -> Config:
        config = ConfigSchema.load(json.load(file_contents))
        assert isinstance(config, Config)
        return config

    def yaml_parser(file_contents: Any) -> Config:
        config = ConfigSchema.load(yaml.safe_load(file_contents))
        assert isinstance(config, Config)
        return config

    return {
        'json': json_parser,
        'yaml': yaml_parser
    }[file_format]


@dataclass
class Template:
    name: str

    def load(self, env: Environment):
        return env.get_template(f'{self.name}.jinja')


def generate_jinja_templates(config: Config, out_dir: str):
    environment = Environment(
        loader=PackageLoader('splugh'),
        autoescape=select_autoescape()
    )

    templates = [
        Template('index.html'),
        Template('index.js'),
    ]

    for template in templates:
        with open(os.path.join(out_dir, template.name),
                  '+w',
                  encoding='utf-8') as file:
            file.write(template.load(environment).render(config=config))


def main() -> int:
    parser = argparse.ArgumentParser(
        sys.argv[0],
        description='A program to generate a landing page.'
    )

    parser.add_argument(
        dest='source',
        help='The source yaml file',
        type=str,
        metavar='SRC'
    )

    parser.add_argument(
        '--output-directory',
        '-o',
        dest='output_directory',
        type=str,
        help='The output directory. splugh_dist/ by default.'
    )

    parser.add_argument(
        '--type', '-t',
        dest='format',
        type=str,
        help='The input file format. The default is selected from file type.',
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        dest='force',
        default=False,
        help='Creates the output regardless of -o existing'
    )

    args = parser.parse_args()

    file_path = os.path.abspath(args.source)
    file_format = args.format \
        if args.format is not None \
        else parse_ext_to_format(file_path.rsplit('.', 1)[1])
    out_dir = os.path.join(
        os.getcwd(),
        args.output_directory
        if args.output_directory is not None
        else 'splugh_dist'
    )

    if os.path.exists(out_dir):
        if args.force:
            shutil.rmtree(out_dir)
        else:
            print(f'{out_dir} already exists. Refusing to operate.',
                  file=sys.stderr)
            return 2

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            config = get_config_parser(file_format)(file)
    except ValidationError as err:
        print(err.messages, file=sys.stderr)
        return 1

    os.mkdir(out_dir)
    generate_jinja_templates(config, out_dir)

    return 0


if __name__ == '__main__':
    sys.exit(main())
