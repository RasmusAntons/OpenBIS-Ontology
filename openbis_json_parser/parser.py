import datetime
import json
import tempfile
import pathlib

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD, OWL

ns=Namespace('http://example.com/')
def load_ontology():
    with tempfile.TemporaryDirectory() as tmpdir:
        g = Graph()
        g.parse(str(pathlib.Path(__file__).parent.parent / 'openbis.ttl'))
    return g

OBIS=Namespace('https://purl.matolab.org/openbis/')
obis=load_ontology()

def get_obis_entity(string: str):
    hits=list(obis[:OBIS.openbis_json_key:Literal(string)])
    if hits:
        return hits[0]
    else:
        return None

def get_custom_props(string: str, graph):
    hits=list(graph[:OBIS.code:Literal(string)])
    if hits:
        return hits[0]
    else:
        return None

def write_ontology(onto, target_file, target_format):
    if target_format in ('ntriples', 'nquads', 'rdfxml'):
        onto.save(target_file, format=target_format)
    elif target_format in ('turtle', 'ttl', 'json-ld'):
        if isinstance(target_file, str):
            with open(target_file, 'wb') as f:
                f.write(onto.serialize(format=target_format).encode('utf-8'))
        else:
            target_file.write(onto.serialize(format=target_format).encode('utf-8'))


def parse_dict(data):
    result = Graph()
    iterate_json(data,result)
    result=fix_iris(result)
    return result


def parse_json(file_path):
    with open(file_path) as f:
        data = json.load(f)
    return parse_dict(data)

def create_instance(data: dict):
    if all(prop in data.keys() for prop in ['@id','@type']):
        id=str(data['@id'])
        o_class=get_obis_entity(data['@type'])
        if o_class:
            return ns[id],o_class
        else:
            return None, None  
    else:
        return None, None  
        

def iterate_json(data, graph):
    if isinstance(data, dict):
        entity, e_class = create_instance(data)
        if entity and e_class:
            graph.add((entity,RDF.type,e_class))
           
        for key, value in data.items():
            if key=="properties" and isinstance(value,dict):
                # lookup in graph 
                for prop_key, prop_value in value.items():
                    obj_prop=get_custom_props(prop_key,graph)
                    if obj_prop:
                        #print(prop_key,obj_prop,prop_value)
                        graph.add((entity,obj_prop,Literal(str(prop_value))))
            elif isinstance(value, (dict, list)):
                iterate_json(value,graph)
            else:
                #print(key)
                annotation=get_obis_entity(key)
                if not value:
                    continue
                elif entity and annotation and key in ['registrationDate','modificationDate']:
                    timestamp = value / 1000  # convert milliseconds to seconds
                    dt = datetime.datetime.fromtimestamp(timestamp)
                    iso_string = dt.isoformat()
                    graph.add((entity,annotation,Literal(str(iso_string))))
                elif entity and annotation and key in ['project','space','experiment']:
                    #print(value,type(value))
                    graph.add((entity,annotation,ns[str(value)]))
                    
                elif entity and annotation and isinstance(value,str):
                    graph.add((entity,annotation,Literal(value)))
                    #print(key, ":", value, annotation)
                pass
    elif isinstance(data, list):
        for item in data:
            iterate_json(item,graph)

def replace_iris(old: URIRef, new: URIRef, graph: Graph):
    ### replaces al iri of all tripple in a graph with the value of relation
    old_triples = list(graph[old: None: None])
    for triple in old_triples:
        graph.remove((old, triple[0], triple[1]))
        graph.add((new, triple[0], triple[1]))
    old_triples = list(graph[None : None: old])
    for triple in old_triples:
        graph.remove((triple[0], triple[1],old))
        graph.add((triple[0], triple[1], new))
    old_triples = list(graph[None : old : None])
    for triple in old_triples:
        graph.remove((triple[0] ,old, triple[1]))
        graph.add((triple[0], new, triple[1]))

def fix_iris(graph):
    # replaces the iris of entties by attached values of code or permId
    for entity_uri, _, value in graph.triples((None, OBIS.code, None)):
        new=ns[value]        
        replace_iris(entity_uri,new,graph)
    # if the have a permId better use that
    for entity_uri, _, value in graph.triples((None, OBIS.code, None)):
    
    #replace_iris(ns,OBIS.code,graph)
    return graph