class BencodingError(Exception):
    pass


def encode(item):
    if isinstance(item, int):
        return _bencode_int(item)
    elif isinstance(item, str):
        return _bencode_string(item)
    elif isinstance(item, bytes):
        return _bencode_bytes(item)
    elif isinstance(item, list):
        return _bencode_list(item)
    elif isinstance(item, dict):
        return _bencode_dict(item)
    else:
        raise BencodingError(f'Unsupported type: {type(item)}')


def _bencode_int(i):
    return f'i{i}e'.encode()

def _bencode_string(s):
    try:
        byte_string = s.encode('ascii')
    except UnicodeEncodeError as e:
        raise BencodingError(f'Invalid string provided. Must be ascii') from e

    return _bencode_bytes(byte_string)

def _bencode_bytes(b):
    return f'{len(b)}:'.encode() + b

def _bencode_list(l):
    bencoded_items = [b'l']
    for item in l:
        bencoded_items.append(encode(item))
    bencoded_items.append(b'e')
    return b''.join(bencoded_items)

def _bencode_dict(d):
    bencoded_items = [b'd']

    for k, v in d.items():
        if not isinstance(k, str):
            raise BencodingError(f'Dictionary key must be str, not: {type(k)}')

        bencoded_items.append(_bencode_string(k))
        bencoded_items.append(encode(v))

    bencoded_items.append(b'e')
    return b''.join(bencoded_items)


def decode(encoded):
    encoded = memoryview(encoded)
    item, leftover = _bdecode(encoded)
    if leftover:
        raise BencodingError(f'Failed to decode entire content. Leftover length: {len(leftover)}')

    return item


def _bdecode(data):
    first_byte = data[0]

    if first_byte == 105:
        return _bdecode_int(data)
    elif 48 <= first_byte <= 57:
        return _bdecode_bytes(data)
    elif first_byte == 108:
        return _bdecode_list(data)
    elif first_byte == 100:
        return _bdecode_dict(data)
    else:
        raise BencodingError(f'Invalid item start byte: {first_byte}')

def _bdecode_int(data):
    underlying_string_index = len(data.obj) - data.nbytes
    delimiter_index = data.obj.find(b'e', underlying_string_index) - underlying_string_index
    if delimiter_index == -1:
        raise BencodingError(f'Failed to determine integer end. Data: {data}')

    integer_body = data[1:delimiter_index]
    try:
        integer = int(integer_body)
    except ValueError as e:
        raise BencodingError(f'Invalid integer') from e

    return integer, data[delimiter_index+1:]

def _bdecode_bytes(data):
    underlying_string_index = len(data.obj) - data.nbytes
    delimiter_index = data.obj.find(b':', underlying_string_index) - underlying_string_index
    if delimiter_index == -1:
        raise BencodingError(f'Failed to determine string length end. Data: {data.obj[underlying_string_index:]}')

    length_body = data[:delimiter_index]
    try:
        length = int(length_body)
    except ValueError as e:
        raise BencodingError(f'Invalid string - bad length') from e

    data = data[delimiter_index+1:]
    if len(data) < length:
        raise BencodingError(f'Invalid string - too long. Length: {length}. '
                             f'Actual left data length: {len(data)}')

    return data[:length].tobytes(), data[length:]

def _bdecode_list(data):
    items = []
    data = data[1:]

    while data[0] != 101:
        item, data = _bdecode(data)
        items.append(item)

    return items, data[1:]

def _bdecode_dict(data):
    items = {}
    data = data[1:]

    while data[0] != 101:
        key, data = _bdecode(data)
        if not isinstance(key, bytes):
            raise BencodingError(f'Reached dictionary key which is of type {type(key)}')

        try:
            key = key.decode('ascii')
        except UnicodeDecodeError as e:
            raise BencodingError(f'Invalid dictionary key string {key}') from e

        value, data = _bdecode(data)
        items[key] = value

    return items, data[1:]

