import datetime
import json
import tempfile
import pathlib
from urllib.parse import urljoin

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


def _find_or_create(onto, cls, data, namespace=None):
    if data is None:
        return None
    obj = next(filter(lambda e: e.code == data['code'], onto.get_instances_of(cls)), None)
    if obj is None:
        obj = add_data(onto, data, namespace=namespace)
    return obj


def add_sample(onto, data, namespace=None):
    sample = onto.Object(name=data['permId']['permId'], namespace=namespace)
    sample.identifier = data['identifier']['identifier']
    sample.code = data.get('code')
    sample.project = _find_or_create(onto, onto.Project, data.get('project'), namespace=namespace)
    sample.space = _find_or_create(onto, onto.Space, data.get('space'), namespace=namespace)
    sample.type = _find_or_create(onto, onto.ObjectType, data.get('type'), namespace=namespace)
    for p_code, p_value in data.get('properties', {}).items():
        p = onto.Property(name=f'{sample.name}.{p_code}', namespace=namespace)
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


def add_sample_type(onto, data, namespace=None):
    sample_type = onto.ObjectType(name=data['permId']['permId'], namespace=namespace)
    sample_type.code = data.get('code')
    sample_type.description = data.get('description')
    for pa in data.get('propertyAssignments', []):
        sample_type.propertyAssignments.append(add_property_assignment(onto, pa, namespace=namespace))
    return sample_type


def add_property_assignment(onto, data, namespace=None):
    perm_id = data['permId']['entityTypeId']['permId'] + '.' + data['permId']['propertyTypeId']['permId']
    pa = onto.PropertyAssignment(name=perm_id, namespace=namespace)
    pa.ordinal = data.get('ordinal')
    pa.mandatory = data.get('mandatory')
    pa.type = _find_or_create(onto, onto.PropertyType, data.get('propertyType'), namespace=namespace)
    pa.registrationDate = datetime.datetime.fromtimestamp(data['registrationDate'] / 1000)
    return pa


def add_property_type(onto, data, namespace=None):
    pt = onto.PropertyType(name=data['permId']['permId'], namespace=namespace)
    pt.code = data.get('code')
    pt.label = data.get('label')
    pt.description = data.get('description')
    pt.dataType = data.get('dataType')
    return pt


def add_project(onto, data, namespace=None):
    project = onto.Project(name=data['permId']['permId'], namespace=namespace)
    project.permID = data['permId']['permId']
    project.identifier = data['identifier']['identifier']
    project.code = data.get('code')
    project.description = data.get('description')
    project.registrationDate = datetime.datetime.fromtimestamp(data['registrationDate'] / 1000)
    project.space = _find_or_create(onto, onto.Space, data.get('space'), namespace=namespace)
    return project


def add_collection(onto, data, namespace=None):
    collection = onto.Collection(name=data['permId']['permId'], namespace=namespace)
    collection.permId = data['permId']['permId']
    collection.identifier = data['identifier']['identifier']
    collection.code = data.get('code')
    collection.registrationDate = datetime.datetime.fromtimestamp(data['registrationDate'] / 1000)
    return collection


def add_space(onto, data, namespace=None):
    space = onto.Space(name=data['permId']['permId'], namespace=namespace)
    space.permID = data['permId']['permId']
    space.code = data.get('code')
    space.description = data.get('description')
    space.registrationDate = datetime.datetime.fromtimestamp(data['registrationDate'] / 1000)
    return space


def add_data(onto, data, namespace=None):
    match data.get('@type'):
        case 'as.dto.sample.Sample':
            return add_sample(onto, data, namespace=namespace)
        case 'as.dto.sample.SampleType':
            return add_sample_type(onto, data, namespace=namespace)
        case 'as.dto.property.PropertyAssignment':
            return add_property_assignment(onto, data, namespace=namespace)
        case 'as.dto.property.PropertyType':
            return add_property_type(onto, data, namespace=namespace)
        case 'as.dto.experiment.Experiment':
            return add_collection(onto, data, namespace=namespace)
        case 'as.dto.project.Project':
            return add_project(onto, data, namespace=namespace)
        case 'as.dto.space.Space':
            return add_space(onto, data, namespace=namespace)
        case _:
            raise Exception(f'invalid data type: {data.get("@type")}')


def parse_dict(data, base_url=None):
    onto = load_ontology()
    for entity in data.values():
        if base_url is None:
            namespace = None
        else:
            namespace = onto.get_namespace(urljoin(base_url, '/openbis/webapp/openbismantic/entity'))
        add_data(onto, entity, namespace=namespace)
    return onto


def parse_json(file_path, base_url=None):
    with open(file_path) as f:
        data = json.load(f)
    return parse_dict(data, base_url=base_url)
