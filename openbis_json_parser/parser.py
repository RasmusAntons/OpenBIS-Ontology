import datetime
import json
import tempfile
import pathlib

import owlready2 as owl
import rdflib


def load_ontology():
    with tempfile.TemporaryDirectory() as tmpdir:
        g = rdflib.Graph()
        g.parse(str(pathlib.Path(__file__).parent.parent / 'openbis.ttl'))
        g.serialize(format='ntriples', destination=pathlib.Path(tmpdir, 'openbis.nt'), encoding='utf-8')
        onto = owl.get_ontology(str(pathlib.Path(tmpdir, 'openbis.nt'))).load()
    return onto


def write_ontology(onto, target_file, target_format):
    if target_format in ('ntriples', 'nquads', 'rdfxml'):
        onto.save(target_file, format=target_format)
    elif target_format in ('turtle', 'ttl', 'json-ld'):
        with tempfile.TemporaryDirectory() as tmpdir:
            onto.save(str(pathlib.Path(tmpdir, 'openbis.nt')), format='ntriples')
            g = rdflib.Graph()
            g.parse(str(pathlib.Path(tmpdir, 'openbis.nt')))
        if isinstance(target_file, str):
            with open(target_file, 'wb') as f:
                f.write(g.serialize(format=target_format).encode('utf-8'))
        else:
            target_file.write(g.serialize(format=target_format).encode('utf-8'))


def _find_or_create(instance, cls, data):
    if data is None:
        return None
    obj = next(filter(lambda e: e.code == data['code'], instance.namespace.get_instances_of(cls)), None)
    if obj is None:
        obj = add_data(instance, data)
    return obj


def add_sample(instance, data):
    onto = instance.namespace
    sample = onto.Object()
    sample.permID = data['permId']['permId']
    sample.identifier = data['identifier']['identifier']
    sample.code = data.get('code')
    sample.project = _find_or_create(instance, onto.Project, data.get('project'))
    sample.space = _find_or_create(instance, onto.Space, data.get('space'))
    sample.type = _find_or_create(instance, onto.ObjectType, data.get('type'))
    for p_code, p_value in data.get('properties', {}).items():
        p = onto.Property()
        p.type = next(filter(lambda e: e.code == p_code, onto.get_instances_of(onto.PropertyType)), None)
        if p.type is None:
            raise Exception(f'invalid property type {p_type}')
        match p.type.dataType:
            case 'TIMESTAMP':
                p.propertyValue = datetime.datetime.strptime(p_value, '%Y-%m-%d %H:%M:%S +0000')
            case 'VARCHAR':
                p.propertyValue = p_value
            case 'REAL':
                p.propertyValue = float(p_value)
            case _:
                raise Exception(f'invalid data type: {p.type.dataType}')
        sample.properties.append(p)
    return sample


def add_sample_type(instance, data):
    onto = instance.namespace
    sample_type = onto.ObjectType()
    sample_type.code = data.get('code')
    sample_type.description = data.get('description')
    for pa in data.get('propertyAssignments', []):
        sample_type.propertyAssignments.append(add_property_assignment(instance, pa))
    return sample_type


def add_property_assignment(instance, data):
    onto = instance.namespace
    pa = onto.PropertyAssignment()
    pa.ordinal = data.get('ordinal')
    pa.mandatory = data.get('mandatory')
    pa.type = _find_or_create(instance, onto.PropertyType, data.get('propertyType'))
    pa.registrationDate = datetime.datetime.fromtimestamp(data['registrationDate'] / 1000)
    return pa


def add_property_type(instance, data):
    onto = instance.namespace
    pt = onto.PropertyType()
    pt.code = data.get('code')
    pt.label = data.get('label')
    pt.description = data.get('description')
    pt.dataType = data.get('dataType')
    return pt


def add_project(instance, data):
    onto = instance.namespace
    project = onto.Project()
    project.permID = data['permId']['permId']
    project.identifier = data['identifier']['identifier']
    project.code = data.get('code')
    project.description = data.get('description')
    project.registrationDate = datetime.datetime.fromtimestamp(data['registrationDate'] / 1000)
    project.space = _find_or_create(instance, onto.Space, data.get('space'))
    return project


def add_collection(instance, data):
    onto = instance.namespace
    collection = onto.Collection()
    collection.permId = data['permId']['permId']
    collection.identifier = data['identifier']['identifier']
    collection.code = data.get('code')
    collection.registrationDate = datetime.datetime.fromtimestamp(data['registrationDate'] / 1000)
    return collection


def add_space(instance, data):
    onto = instance.namespace
    space = onto.Space()
    space.permID = data['permId']['permId']
    space.code = data.get('code')
    space.description = data.get('description')
    space.registrationDate = datetime.datetime.fromtimestamp(data['registrationDate'] / 1000)
    return space


def add_data(instance, data):
    match data.get('@type'):
        case 'as.dto.sample.Sample':
            return add_sample(instance, data)
        case 'as.dto.sample.SampleType':
            return add_sample_type(instance, data)
        case 'as.dto.property.PropertyAssignment':
            return add_property_assignment(instance, data)
        case 'as.dto.property.PropertyType':
            return add_property_type(instance, data)
        case 'as.dto.experiment.Experiment':
            return add_collection(instance, data)
        case 'as.dto.project.Project':
            return add_project(instance, data)
        case 'as.dto.space.Space':
            return add_space(instance, data)
        case _:
            raise Exception(f'invalid data type: {data.get("@type")}')


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
