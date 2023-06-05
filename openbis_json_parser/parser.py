import datetime
import json
import pathlib
import tempfile
import urllib.parse

import rdflib
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, XSD, OWL

# plugin api endpoint for permIds should be here
default_ns = Namespace('https://openbis.matolab.org/openbismantic/')


def load_ontology():
    g = Graph()
    g.parse(str(pathlib.Path(__file__).parent.parent / 'openbis.ttl'))
    return g


OBIS = Namespace('https://purl.matolab.org/openbis/')
obis = load_ontology()


def _get_ns(base_url=None):
    if base_url is None:
        return default_ns
    return Namespace(urllib.parse.urljoin(base_url, 'openbismantic/'))


def get_obis_entity(string: str):
    hits = list(obis[:OBIS.openbis_json_key:Literal(string)])
    if hits:
        return hits[0]
    else:
        return None


def get_custom_props(string: str, graph):
    hits = list(graph[:OBIS.code:Literal(string)])
    if hits:
        return hits[0]
    else:
        return None


def write_ontology(onto, target_file, target_format):
    if isinstance(target_file, str):
        with open(target_file, 'wb') as f:
            f.write(onto.serialize(format=target_format).encode('utf-8'))
    else:
        target_file.write(onto.serialize(format=target_format).encode('utf-8'))


def parse_dict(data, base_url=None):
    result = Graph()
    result.bind('obis', OBIS)
    result.bind('data', _get_ns(base_url))
    iterate_json(data, result, base_url=base_url)
    result = fix_iris(result, base_url=base_url)
    return result


def parse_json(file_path, base_url=None):
    with open(file_path) as f:
        data = json.load(f)
    return parse_dict(data, base_url=base_url)


def create_instance_triple(data: dict, base_url=None):
    if all(prop in data.keys() for prop in ['@id', '@type']):
        instance_id = str(data['@id'])
        o_class = get_obis_entity(data['@type'])
        if o_class:
            return _get_ns(base_url)[instance_id], o_class
        else:
            return None, None
    else:
        return None, None


def iterate_json(data, graph, last_entity=None, base_url=None):
    if isinstance(data, dict):
        # lookup if the id and type in dict result in a ontology entity
        entity, e_class = create_instance_triple(data, base_url=base_url)
        if entity and e_class:
            # if the entity is a Identifier, only create it if it relates to entity previously created
            if e_class in [OBIS.PermanentIdentifier, OBIS.Identifier]:
                if last_entity:
                    # add the triple defining the entity
                    graph.add((entity, RDF.type, e_class))
                    # add object properties
                    graph.add((last_entity, OBIS.has_identifier, entity))
                    graph.add((entity, OBIS.is_identifier_of, last_entity))
                else:
                    entity = None
            else:
                # add the triple defining the entity
                graph.add((entity, RDF.type, e_class))

        for key, value in data.items():
            # if the key is properties all json keys in that dict are relations to openbis properties followed by there values
            if key == "properties" and isinstance(value, dict):
                # lookup in graph 
                for prop_key, prop_value in value.items():
                    obj_prop = get_custom_props(prop_key, graph)
                    if obj_prop:
                        # print(prop_key,obj_prop,prop_value)
                        graph.add((entity, obj_prop, Literal(str(prop_value))))
            elif isinstance(value, (dict, list)):
                # recursively inter over all jason objects
                iterate_json(value, graph, entity, base_url=base_url)
                annotation = get_obis_entity(key)
                if entity and annotation and key in ['project', 'space', 'experiment']:
                    graph.add((entity, annotation, _get_ns(base_url)[str(value['@id'])]))
            else:
                # if its no dict or list test if its kind of object/data/annotation property and set it
                annotation = get_obis_entity(key)
                # print(key,value)
                # skip if the value is not set
                if not value:
                    continue
                elif entity and annotation and key in ['registrationDate', 'modificationDate']:
                    # timestamp values are transformed to iso datetime strings
                    timestamp = value / 1000  # convert milliseconds to seconds
                    dt = datetime.datetime.fromtimestamp(timestamp)
                    iso_string = dt.isoformat()
                    graph.add((entity, annotation, Literal(str(iso_string), datatype=XSD.dateTimeStamp)))
                elif entity and annotation and key in ['email']:
                    graph.add((entity, annotation, URIRef("mailto:{}".format(value))))
                elif entity and annotation and key in ['project', 'space', 'experiment']:
                    # these json keyword point to integers which relates to other entities
                    graph.add((entity, annotation, _get_ns(base_url)[str(value)]))
                elif entity and annotation and isinstance(value, str):
                    graph.add((entity, annotation, Literal(value)))

    elif isinstance(data, list):
        for item in data:
            iterate_json(item, graph, base_url=base_url)


def replace_iris(old: URIRef, new: URIRef, graph: Graph):
    # replaces all iri of all triple in a graph with the value of relation
    old_triples = list(graph[old: None: None])
    for triple in old_triples:
        graph.remove((old, triple[0], triple[1]))
        graph.add((new, triple[0], triple[1]))
    old_triples = list(graph[None: None: old])
    for triple in old_triples:
        graph.remove((triple[0], triple[1], old))
        graph.add((triple[0], triple[1], new))
    old_triples = list(graph[None: old: None])
    for triple in old_triples:
        graph.remove((triple[0], old, triple[1]))
        graph.add((triple[0], new, triple[1]))


def fix_iris(graph, base_url=None):
    # replace int iris with permids if possible
    for permid in graph[: RDF.type: OBIS.PermanentIdentifier]:
        permid_value = graph.value(permid, RDF.value)
        identifies = graph.value(permid, OBIS.is_identifier_of)
        identifies_type = graph.value(identifies, RDF.type).split('/')[-1].lower()
        new = _get_ns(base_url)[f'{identifies_type}/{permid_value}']
        replace_iris(identifies, new, graph)

    # replace iri of created object properties with value of code if possible
    for property in graph[: RDF.type: OWL.ObjectProperty]:
        code_value = graph.value(property, OBIS.code)
        if code_value:
            new = _get_ns(base_url)[code_value]
            replace_iris(property, new, graph)

    for identifier in graph[: RDF.type: OBIS.Identifier]:
        replace_iris(identifier, rdflib.BNode(), graph)

    for identifier in graph[: RDF.type: OBIS.PermanentIdentifier]:
        replace_iris(identifier, rdflib.BNode(), graph)
    return graph
