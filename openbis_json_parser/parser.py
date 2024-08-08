import ast
import json
import pathlib
import re
import urllib.parse
from datetime import datetime
from typing import Tuple, Union

from dateutil.parser import parse as date_parse
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

# plugin api endpoint for permIds should be here
default_ns = Namespace("https://openbismantic.matolab.org/openbismantic/")


def load_ontology():
    g = Graph()
    g.parse(str(pathlib.Path(__file__).parent.parent / "openbis.ttl"))
    return g


OBIS = Namespace("https://w3id.org/matolab/openbis/")
QUDT = Namespace("http://qudt.org/schema/qudt/")
OA = Namespace("http://www.w3.org/ns/oa#")

obis = load_ontology()

TEMP = Namespace("https://example.com/")


def _get_ns(base_url=None):
    if base_url is None:
        return default_ns
    return Namespace(urllib.parse.urljoin(base_url, "openbismantic/"))


def get_obis_entity(string: str):
    hits = list(obis[: OBIS.openbis_json_key : Literal(string)])
    if hits:
        return hits[0]
    else:
        return None


def get_custom_props(string: str, graph):
    hits = list(graph[: OBIS.code : Literal(string)])
    if hits:
        return hits[0]
    else:
        return None


def is_date(string, fuzzy=False) -> bool:
    try:
        date_parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False


def get_value_type(string: str) -> Tuple:
    string = str(string)
    # remove spaces and replace , with . and
    string = string.strip().replace(",", ".")
    if len(string) == 0:
        return "BLANK", None
    try:
        t = ast.literal_eval(string)
    except ValueError:
        return "TEXT", XSD.string
    except SyntaxError:
        if is_date(string):
            return "DATE", XSD.dateTime
        else:
            return "TEXT", XSD.string
    else:
        if type(t) in [int, float, bool]:
            if type(t) is int:
                return "INT", XSD.integer
            if t in set((True, False)):
                return "BOOL", XSD.boolean
            if type(t) is float:
                return "FLOAT", XSD.double
        else:
            # return 'TEXT'
            return "TEXT", XSD.string


def describe_value(graph, node, relation, value_string: str):
    val_type = get_value_type(value_string)
    if val_type:
        body = BNode()
        graph.add((node, relation, body))

    if val_type[0] == "INT":
        graph.add((body, RDF.type, QUDT.QuantityValue))
        graph.add(
            (
                body,
                QUDT.value,
                Literal(int(value_string), datatype=val_type[1]),
            )
        )
    elif val_type[0] == "BOOL":
        body = BNode()
        graph.add((body, RDF.type, QUDT.QuantityValue))
        graph.add(
            (
                body,
                QUDT.value,
                Literal(bool(value_string), datatype=val_type[1]),
            )
        )
    elif val_type[0] == "FLOAT":
        if isinstance(value_string, str):
            # replace , with . as decimal separator
            value_string = value_string.strip().replace(",", ".")
        graph.add((body, RDF.type, QUDT.QuantityValue))
        graph.add(
            (
                body,
                QUDT.value,
                Literal(float(value_string), datatype=val_type[1]),
            )
        )
    elif val_type[0] == "DATE":
        print(value_string)
        body = BNode()
        graph.add((body, RDF.type, QUDT.QuantityValue))
        graph.add(
            (
                body,
                QUDT.value,
                Literal(
                    str(date_parse(value_string).isoformat()),
                    datatype=val_type[1],
                ),
            )
        )
    else:
        graph.add((body, RDF.type, OA.Annotation))
        graph.add(
            (
                body,
                OA.hasLiteralBody,
                Literal(value_string.strip(), datatype=val_type[1]),
            )
        )


def write_ontology(onto, target_file, target_format):
    if isinstance(target_file, str):
        with open(target_file, "wb") as f:
            f.write(onto.serialize(format=target_format).encode("utf-8"))
    else:
        target_file.write(onto.serialize(format=target_format).encode("utf-8"))


def parse_dict(data, base_url=None):
    result = Graph()
    result.bind("obis", OBIS)
    result.bind("qudt", QUDT)
    result.bind("oa", OA)

    # result.bind('data', _get_ns(base_url))
    iterate_json(data, result, base_url=base_url)
    result = fix_iris(result, base_url=base_url)
    return result


def parse_json(file_path, base_url=None):
    with open(file_path) as f:
        data = json.load(f)
    return parse_dict(data, base_url=base_url)


def create_instance_triple(data: dict, base_url=None):
    entity = None
    o_class = None
    parent = None
    if all(prop in data.keys() for prop in ["@type"]):
        instance_id = str(data["@id"])
        o_class = get_obis_entity(data["@type"])
        if o_class:
            entity = URIRef(instance_id, TEMP)
        if data["@type"] == "as.dto.sample.SampleType":
            parent = OBIS.Object
        elif data["@type"] == "as.dto.experiment.ExperimentType":
            parent = OBIS.Collection
    return entity, o_class, parent


def add_identifier(
    graph: Graph,
    entity: URIRef,
    identifier: Union(URIRef, BNode),
    identifier_class: URIRef = OBIS.Identifier,
    label: str = "",
):
    if entity:
        # add the triple defining the entity only if the identifier is attached to something
        graph.add((identifier, RDF.type, identifier_class))
        if label:
            graph.add(
                (
                    identifier,
                    RDF.value,
                    Literal(re.sub("[$:]", "", label)),
                )
            )
        # add object properties
        graph.add((entity, OBIS.has_identifier, identifier))
        graph.add((identifier, OBIS.is_identifier_of, entity))
        return identifier
    else:
        return None


def create_new_property(graph: Graph, prop_key: str):
    # create a new ObjectProperty
    obj_prop = BNode()
    obj_prop_id = BNode()
    graph.add((obj_prop, RDF.type, OWL.ObjectProperty))
    # add identifier
    obj_prop_id = add_identifier(
        graph, obj_prop, obj_prop_id, OBIS.PermanentIdentifier, label=prop_key
    )
    print("created a custom object property with permid: {}".format(prop_key))
    return obj_prop


def iterate_json(data, graph, last_entity=None, base_url=None):
    if isinstance(data, dict):
        # lookup if the id and type in dict result in a ontology entity
        entity, e_class, parent = create_instance_triple(data, base_url=base_url)
        if entity and e_class:
            # if the entity is a Identifier, only create it if it relates to entity previously created
            if e_class in [OBIS.PermanentIdentifier, OBIS.Identifier]:
                entity = add_identifier(graph, last_entity, e_class)
            else:
                # add the triple defining the entity
                graph.add((entity, RDF.type, e_class))
            if parent:
                print(
                    "new class {} of type {} has parent {}, adding subClassOf relation".format(
                        entity, e_class, parent
                    )
                )
                graph.add((entity, RDFS.subClassOf, parent))

            for key, value in data.items():
                # if the key is properties all json keys in that dict are relations to openbis properties followed by there values
                if key == "fetchOptions":
                    continue
                elif key == "properties" and isinstance(value, dict):
                    # lookup in graph
                    for prop_key, prop_value in value.items():
                        obj_prop = get_custom_props(prop_key, graph)
                        # print(entity, key, prop_key, prop_value, obj_prop)
                        if not obj_prop:
                            # create a new ObjectProperty
                            obj_prop = create_new_property(graph, prop_key)
                        describe_value(graph, entity, obj_prop, prop_value)
                        # graph.add((entity, obj_prop, Literal(str(prop_value))))

                elif isinstance(value, dict):
                    # recursively inter over all json objects
                    iterate_json(value, graph, entity, base_url=base_url)
                    # add the ObjectProperty to the created instance
                    annotation = get_obis_entity(key)
                    # identifiers are handled already
                    if entity and key not in ["permId", "identifier", "id"]:
                        if (
                            annotation and "@id" in value.keys()
                        ):  # and key in ['project', 'space', 'experiment']:
                            graph.add(
                                (
                                    entity,
                                    annotation,
                                    URIRef(str(value["@id"]), TEMP),
                                )
                            )
                        else:
                            print("unhandled relation to dict entry")
                            print(entity, e_class, annotation, key)
                elif isinstance(value, list):
                    # recursively inter over all json objects
                    iterate_json(value, graph, entity, base_url=base_url)
                    # see if an entity is created and relate it if necessary
                    annotation = get_obis_entity(key)
                    if entity and annotation:
                        for item in value:
                            if isinstance(item, dict) and "@id" in item.keys():
                                graph.add(
                                    (
                                        entity,
                                        annotation,
                                        URIRef(str(item["@id"]), TEMP),
                                    )
                                )
                    else:
                        print("unhandled relation to list entry")
                        print(entity, e_class, annotation, key)
                else:
                    # if its no dict or list test if its kind of object/data/annotation property and set it
                    annotation = get_obis_entity(key)
                    # print(key,value)
                    # skip if the value is not set
                    if not value:
                        continue
                    # date value should be transformed to iso format
                    elif (
                        entity
                        and annotation
                        and key in ["registrationDate", "modificationDate"]
                    ):
                        # timestamp values are transformed to iso datetime strings
                        timestamp = value / 1000  # convert milliseconds to seconds
                        dt = datetime.fromtimestamp(timestamp)
                        iso_string = dt.isoformat()
                        graph.add(
                            (
                                entity,
                                annotation,
                                Literal(str(iso_string), datatype=XSD.dateTimeStamp),
                            )
                        )
                    # emails should have mailto prefix
                    elif entity and annotation and key in ["email"]:
                        graph.add(
                            (
                                entity,
                                annotation,
                                URIRef("mailto:{}".format(value)),
                            )
                        )
                    # these are properties haveing a singular entry which is a relativ id in the json output
                    elif (
                        entity
                        and annotation
                        and key in ["project", "space", "experiment"]
                    ):
                        # these json keyword point to integers which relates to other entities
                        # graph.add((entity, annotation, _get_ns(base_url)[str(value)]))
                        graph.add((entity, annotation, URIRef(str(value), TEMP)))
                    elif entity and annotation and isinstance(value, str):
                        graph.add((entity, annotation, Literal(value)))

    elif isinstance(data, list):
        for item in data:
            iterate_json(item, graph, base_url=base_url)


def replace_iris(old: URIRef, new: URIRef, graph: Graph):
    # replaces all iri of all triple in a graph with the value of relation
    old_triples = list(graph[old:None:None])
    for triple in old_triples:
        graph.remove((old, triple[0], triple[1]))
        graph.add((new, triple[0], triple[1]))
    old_triples = list(graph[None:None:old])
    for triple in old_triples:
        graph.remove((triple[0], triple[1], old))
        graph.add((triple[0], triple[1], new))
    old_triples = list(graph[None:old:None])
    for triple in old_triples:
        graph.remove((triple[0], old, triple[1]))
        graph.add((triple[0], new, triple[1]))


def fix_iris(graph, base_url=None):
    # replace int iris with permids if possible
    for permid in graph[: RDF.type : OBIS.PermanentIdentifier]:
        permid_value = graph.value(permid, RDF.value)
        identifies = graph.value(permid, OBIS.is_identifier_of)
        identifies_type = graph.value(identifies, RDF.type)
        type_str = identifies_type.split("/")[-1].lower()
        # print(identifies,identifies_type)
        if identifies_type in [OWL.Class]:
            type_str = "class"
        elif identifies_type in [OWL.ObjectProperty]:
            type_str = "object_property"
        graph.bind(type_str, _get_ns(base_url)[f"{type_str}/"])
        new = URIRef(f"{type_str}/{permid_value}", _get_ns(base_url))
        replace_iris(identifies, new, graph)
        # print(identifies,new)

    # replace iri of created object properties with value of code if possible
    for property in graph[: RDF.type : OWL.ObjectProperty]:
        code_value = graph.value(property, OBIS.code)
        if code_value:
            new = _get_ns(base_url)[code_value]
            replace_iris(property, new, graph)

    for identifier in graph[: RDF.type : OBIS.Identifier]:
        replace_iris(identifier, BNode(), graph)
    for identifier in graph[: RDF.type : OBIS.PermanentIdentifier]:
        replace_iris(identifier, BNode(), graph)
    return graph
