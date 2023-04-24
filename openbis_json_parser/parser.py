import json
import tempfile
import pathlib

import owlready2 as owl
import rdflib


def load_ontology():
    with tempfile.TemporaryDirectory() as tmpdir:
        g = rdflib.Graph()
        g.parse(str(pathlib.Path(__file__).parent.parent.parent / 'openbis.ttl'))
        g.serialize(format='ntriples', destination=pathlib.Path(tmpdir, 'openbis.nt'), encoding='utf-8')
        onto = owl.get_ontology(str(pathlib.Path(tmpdir, 'openbis.nt'))).load()
    return onto


def add_sample(instance, data):
    onto = instance.namespace
    sample = onto.Object(partOf=instance)
    sample.permID = data['permId']['permId']
    sample.identifier = data['identifier']['identifier']
    sample.code = data['code']
    sample.type = next(filter(lambda e: e.code == data['type']['code'], onto.get_instances_of(onto.ObjectType)), None)
    if sample.type is None:
        sample.type = add_sample_type(instance, data['type'])
    return sample


def add_sample_type(instance, data):
    onto = instance.namespace
    sample_type = onto.ObjectType()
    sample_type.code = data['code']
    sample_type.description = data['description']
    for pa in data['propertyAssignments']:
        add_property_assignment(instance, pa)
    return sample_type


def add_property_assignment(instance, data):
    pass


def add_data(instance, data):
    match data['@type']:
        case 'as.dto.sample.Sample':
            return add_sample(instance, data)
        case 'as.dto.sample.SampleType':
            return add_sample_type(instance, data)
        case 'as.dto.property.PropertyAssignment':
            return add_property_assignment(instance, data)
        case _:
            raise Exception(f'invalid data type: {data["@type"]}')


def parse_dict(data):
    onto = load_ontology()
    instance = onto.Instance()
    for entity in data.values():
        add_data(instance, entity)
    return onto


def parse_json(file_path):
    with open(file_path) as f:
        data = json.load(f)
    return parse_dict(data)
