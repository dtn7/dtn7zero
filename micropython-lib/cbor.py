#!python
# -*- Python -*-

#import math
import math
import utime
import ure
import ustruct
from ubinascii import hexlify
from uio import BytesIO


_CBOR_TYPE_MASK = const(0xE0)  # top 3 bits
_CBOR_INFO_BITS = const(0x1F)  # low 5 bits


_CBOR_UINT    = const(0x00)
_CBOR_NEGINT  = const(0x20)
_CBOR_BYTES   = const(0x40)
_CBOR_TEXT    = const(0x60)
_CBOR_ARRAY   = const(0x80)
_CBOR_MAP     = const(0xA0)
_CBOR_TAG     = const(0xC0)
_CBOR_7       = const(0xE0)  # float and other types

_CBOR_UINT8_FOLLOWS  = const(24)  # 0x18
_CBOR_UINT16_FOLLOWS = const(25)  # 0x19
_CBOR_UINT32_FOLLOWS = const(26)  # 0x1a
_CBOR_UINT64_FOLLOWS = const(27)  # 0x1b
_CBOR_VAR_FOLLOWS    = const(31)  # 0x1f

_CBOR_BREAK  = const(0xFF)

_CBOR_FALSE  = const(_CBOR_7 | 20)
_CBOR_TRUE   = const(_CBOR_7 | 21)
_CBOR_NULL   = const(_CBOR_7 | 22)
_CBOR_UNDEFINED   = const(_CBOR_7 | 23)  # js 'undefined' value

_CBOR_FLOAT16 = const(_CBOR_7 | 25)
_CBOR_FLOAT32 = const(_CBOR_7 | 26)
_CBOR_FLOAT64 = const(_CBOR_7 | 27)

_CBOR_TAG_DATE_STRING = const(0) # RFC3339
_CBOR_TAG_DATE_ARRAY  = const(1) # any number type follows, seconds since 1970-01-01T00:00:00 UTC
_CBOR_TAG_BIGNUM      = const(2) # big endian byte string follows
_CBOR_TAG_NEGBIGNUM   = const(3) # big endian byte string follows
_CBOR_TAG_DECIMAL     = const(4) # [ 10^x exponent, number ]
_CBOR_TAG_BIGFLOAT    = const(5) # [ 2^x exponent, number ]
_CBOR_TAG_BASE64URL   = const(21)
_CBOR_TAG_BASE64      = const(22)
_CBOR_TAG_BASE16      = const(23)
_CBOR_TAG_CBOR        = const(24) # following byte string is embedded CBOR data

_CBOR_TAG_URI             = const(32)
_CBOR_TAG_BASE64URL_STR   = const(33)
_CBOR_TAG_BASE64_STR      = const(34)
_CBOR_TAG_REGEX           = const(35)
_CBOR_TAG_MIME            = const(36) # following text is MIME message, headers, separators and all
_CBOR_TAG_CBOR_FILEHEADER = const(55799) # can open a file with 0xd9d9f7

_CBOR_TAG_BIGNUM_BYTES = ustruct.pack('B', _CBOR_TAG | _CBOR_TAG_BIGNUM)
_CBOR_TAG_NEGBIGNUM_BYTES = ustruct.pack('B', _CBOR_TAG | _CBOR_TAG_NEGBIGNUM)

_MAX_DEPTH = const(100)


def dumps_int(val):
    "return bytes representing int val in CBOR"
    cbor_type = _CBOR_UINT
    cbor_tag= _CBOR_TAG_BIGNUM_BYTES
    if val < 0:
        val = -1 - val
        cbor_type = _CBOR_NEGINT
        cbor_tag= _CBOR_TAG_NEGBIGNUM_BYTES

    if val <= 0x0ffffffffffffffff: #NOT BIGINT
        return _encode_type_num(cbor_type, val)
    outb = _dumps_bignum_to_bytearray(val) #BIGINT

    return cbor_tag + _encode_type_num(_CBOR_BYTES, len(outb)) + outb


def _dumps_bignum_to_bytearray(val):
    n_bytes = int(math.ceil(math.log2(val+1)/8.0))
    return val.to_bytes(n_bytes, 'big')


def dumps_float(val):
    return ustruct.pack("!Bd", _CBOR_FLOAT64, val)


def _encode_type_num(cbor_type, val):
    """For some CBOR primary type [0..7] and an auxiliary unsigned number, return CBOR encoded bytes"""
    assert val >= 0
    if val <= 23:
        return ustruct.pack('B', cbor_type | val)
    if val <= 0x0ff: #UINT8
        return ustruct.pack('BB', cbor_type | _CBOR_UINT8_FOLLOWS, val)
    if val <= 0x0ffff: #UINT16
        return ustruct.pack('!BH', cbor_type | _CBOR_UINT16_FOLLOWS, val)
    if val <= 0x0ffffffff: #UINT32
        return ustruct.pack('!BI', cbor_type | _CBOR_UINT32_FOLLOWS, val)
    if val <= 0x0ffffffffffffffff: #UINT64
        return ustruct.pack('!BQ', cbor_type | _CBOR_UINT64_FOLLOWS, val)
    raise Exception("value too big for CBOR unsigned number: {0!r}".format(val))


def dumps_string(val):
    val = val.encode('utf8')
    return _encode_type_num(_CBOR_TEXT, len(val)) + val


def dumps_bytestring(val):
    return _encode_type_num(_CBOR_BYTES, len(val)) + val


def dumps_bytearray(val):
    return dumps_bytestring(bytes(val))


def dumps_array(arr, sort_keys=False):
    head = _encode_type_num(_CBOR_ARRAY, len(arr))
    parts = [dumps(x, sort_keys=sort_keys) for x in arr]
    return head + b''.join(parts)


def dumps_dict(d, sort_keys=False):
    head = _encode_type_num(_CBOR_MAP, len(d))
    parts = [head]
    if sort_keys:
        for k in sorted(d.keys()):
            v = d[k]
            parts.append(dumps(k, sort_keys=sort_keys))
            parts.append(dumps(v, sort_keys=sort_keys))
    else:
        for k,v in d.items():
            parts.append(dumps(k, sort_keys=sort_keys))
            parts.append(dumps(v, sort_keys=sort_keys))
    return b''.join(parts)


def dumps_bool(b):
    return ustruct.pack('B', _CBOR_TRUE) if b else ustruct.pack('B', _CBOR_FALSE)


def dumps_tag(t, sort_keys=False):
    return _encode_type_num(_CBOR_TAG, t.tag) + dumps(t.value, sort_keys=sort_keys)


def dumps(ob, sort_keys=False):
    if ob is None:
        return ustruct.pack('B', _CBOR_NULL)
    if isinstance(ob, bool):
        return dumps_bool(ob)
    if isinstance(ob, str):
        return dumps_string(ob)
    if isinstance(ob, bytes):
        return dumps_bytestring(ob)
    if isinstance(ob, bytearray):
        return dumps_bytearray(ob)
    if isinstance(ob, (list, tuple)):
        return dumps_array(ob, sort_keys=sort_keys)
    # TODO: accept other enumerables and emit a variable length array
    if isinstance(ob, dict):
        return dumps_dict(ob, sort_keys=sort_keys)
    if isinstance(ob, float):
        return dumps_float(ob)
    if isinstance(ob, int):
        return dumps_int(ob)
    if isinstance(ob, Tag):
        return dumps_tag(ob, sort_keys=sort_keys)
    raise Exception("don't know how to cbor serialize object of type %s", type(ob))


# same basic signature as json.dump, but with no options (yet)
def dump(obj, fp, sort_keys=False):
    """
    obj: Python object to serialize
    fp: file-like object capable of .write(bytes)
    """
    # this is kinda lame, but probably not inefficient for non-huge objects
    # TODO: .write() to fp as we go as each inner object is serialized
    blob = dumps(obj, sort_keys=sort_keys)
    fp.write(blob)


class Tag(object):
    def __init__(self, tag=None, value=None):
        self.tag = tag
        self.value = value

    def __repr__(self):
        return "Tag({0!r}, {1!r})".format(self.tag, self.value)

    def __eq__(self, other):
        if not isinstance(other, Tag):
            return False
        return (self.tag == other.tag) and (self.value == other.value)


def loads(data):
    """
    Parse CBOR bytes and return Python objects.
    """
    if data is None:
        raise ValueError("got None for buffer to decode in loads")
    elif data == b'':
        raise ValueError("got zero length string loads")

    return _loads(BytesIO(data))


def load(fp):
    """
    Parse and return object from fp, a file-like object supporting .read(n)
    """
    return _loads(fp)


def _tag_aux(fp, tb):
    tag = tb & _CBOR_TYPE_MASK
    tag_aux = tb & _CBOR_INFO_BITS
    if tag_aux <= 23:
        aux = tag_aux
    elif tag_aux == _CBOR_UINT8_FOLLOWS:
        data = fp.read(1)
        aux = ustruct.unpack_from("!B", data, 0)[0]
    elif tag_aux == _CBOR_UINT16_FOLLOWS:
        data = fp.read(2)
        aux = ustruct.unpack_from("!H", data, 0)[0]
    elif tag_aux == _CBOR_UINT32_FOLLOWS:
        data = fp.read(4)
        aux = ustruct.unpack_from("!I", data, 0)[0]
    elif tag_aux == _CBOR_UINT64_FOLLOWS:
        data = fp.read(8)
        aux = ustruct.unpack_from("!Q", data, 0)[0]
    else:
        assert tag_aux == _CBOR_VAR_FOLLOWS, "bogus tag {0:02x}".format(tb)
        aux = None

    return tag, tag_aux, aux


def _read_byte(fp):
    tb = fp.read(1)
    if len(tb) == 0:
        # I guess not all file-like objects do this
        raise EOFError()
    return ord(tb)


def _loads_var_array(fp, limit, depth, returntags):
    ob = []
    tb = _read_byte(fp)
    while tb != _CBOR_BREAK:
        ob.append(_loads_tb(fp, tb, limit, depth, returntags))

        tb = _read_byte(fp)
    return ob


def _loads_var_map(fp, limit, depth, returntags):
    ob = {}
    tb = _read_byte(fp)
    while tb != _CBOR_BREAK:
        subk = _loads_tb(fp, tb, limit, depth, returntags)
        subv = _loads(fp, limit, depth, returntags)
        ob[subk] = subv

        tb = _read_byte(fp)
    return ob


def _loads_array(fp, limit, depth, returntags, aux):
    ob = []
    for _ in range(aux):
        ob.append(_loads(fp))
    return ob


def _loads_map(fp, limit, depth, returntags, aux):
    ob = {}
    for _ in range(aux):
        subk = _loads(fp)
        subv = _loads(fp)
        ob[subk] = subv
    return ob


def _loads(fp, limit=None, depth=0, returntags=False):
    "return (object, bytes read)"
    if depth > _MAX_DEPTH:
        raise Exception("Hit CBOR loads recursion depth limit.")

    tb = _read_byte(fp)

    return _loads_tb(fp, tb, limit, depth, returntags)


def _decode_single(single):
    return ustruct.unpack("!f", ustruct.pack("!I", single))[0]


def _loads_tb(fp, tb, limit=None, depth=0, returntags=False):
    if tb == _CBOR_FLOAT16:
        # Adapted from cbor2 unpack_float16()
        data = fp.read(2)
        data = ustruct.unpack('>H', data)[0]

        value = (data & 0x7fff) << 13 | (data & 0x8000) << 16
        if data & 0x7c00 != 0x7c00:
            return math.ldexp(_decode_single(value), 112)
        return _decode_single(value | 0x7f800000)
    elif tb == _CBOR_FLOAT32:
        data = fp.read(4)
        return ustruct.unpack_from("!f", data, 0)[0]
    elif tb == _CBOR_FLOAT64:
        data = fp.read(8)
        return ustruct.unpack_from("!d", data, 0)[0]

    tag, tag_aux, aux = _tag_aux(fp, tb)

    if tag == _CBOR_UINT:
        return aux
    elif tag == _CBOR_NEGINT:
        return -1 - aux
    elif tag == _CBOR_BYTES:
        return  loads_bytes(fp, aux)
    elif tag == _CBOR_TEXT:
        raw = loads_bytes(fp, aux, btag=_CBOR_TEXT)
        return raw.decode('utf8')
    elif tag == _CBOR_ARRAY:
        if aux is None:
            return _loads_var_array(fp, limit, depth, returntags)
        return _loads_array(fp, limit, depth, returntags, aux)
    elif tag == _CBOR_MAP:
        if aux is None:
            return _loads_var_map(fp, limit, depth, returntags)
        return _loads_map(fp, limit, depth, returntags, aux)
    elif tag == _CBOR_TAG:
        if returntags:
            # Don't interpret the tag, return it and the tagged object.
            return Tag(aux, _loads(fp))
        # attempt to interpet the tag and the value into a Python object.
        return tagify(_loads(fp), aux)
    elif tag == _CBOR_7:
        if tb == _CBOR_TRUE:
            return True
        if tb == _CBOR_FALSE:
            return False
        if tb == _CBOR_NULL:
            return None
        if tb == _CBOR_UNDEFINED:
            return None
        raise ValueError("unknown cbor tag 7 byte: {:02x}".format(tb))


def loads_bytes(fp, aux, btag=_CBOR_BYTES):
    # TODO: limit to some maximum number of chunks and some maximum total bytes
    if aux is not None:
        # simple case
        return fp.read(aux)
    # read chunks of bytes
    chunklist = []
    while True:
        tb = fp.read(1)[0]
        if tb == _CBOR_BREAK:
            break
        tag, tag_aux, aux = _tag_aux(fp, tb)
        assert tag == btag, 'variable length value contains unexpected component'
        chunklist.append(fp.read(aux))
    return b''.join(chunklist)


def _bytes_to_biguint(bs):
    #Taken form cbor2 decode_positive_bignum()
    return int(hexlify(bs), 16)


def tagify(ob, aux):
    # TODO: make this extensible?
    # cbor.register_tag_handler(tagnumber, tag_handler)
    # where tag_handler takes (tagnumber, tagged_object)
    if aux == _CBOR_TAG_DATE_STRING:
        # TODO: parse RFC3339 date string
        pass
    if aux == _CBOR_TAG_DATE_ARRAY:
        return utime.localtime(ob)
    if aux == _CBOR_TAG_BIGNUM:
        return _bytes_to_biguint(ob)
    if aux == _CBOR_TAG_NEGBIGNUM:
        return -1 - _bytes_to_biguint(ob)
    if aux == _CBOR_TAG_REGEX:
        # Is this actually a good idea? Should we just return the tag and the raw value to the user somehow?
        return ure.compile(ob)
    return Tag(aux, ob)
