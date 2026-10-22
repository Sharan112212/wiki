"""
Posting-List Compression Module (Tier D).
Implements Delta encoding (gap encoding) and Variable-Byte (VByte) integer compression.
"""
from typing import List, Tuple


def vbyte_encode_number(num: int) -> bytes:
    """Encodes a single non-negative integer using Variable Byte (VByte)."""
    if num < 0:
        raise ValueError(f"VByte only supports non-negative integers: {num}")
    out = bytearray()
    while True:
        b = num & 0x7F
        num >>= 7
        if num == 0:
            out.append(b | 0x80)  # Stop bit: MSB is 1 on the terminal byte
            break
        else:
            out.append(b)  # MSB is 0 on intermediate bytes
    return bytes(out)


def vbyte_encode(numbers: List[int]) -> bytes:
    """Encodes a list of non-negative integers into a contiguous VByte byte string."""
    out = bytearray()
    for n in numbers:
        while True:
            b = n & 0x7F
            n >>= 7
            if n == 0:
                out.append(b | 0x80)
                break
            else:
                out.append(b)
    return bytes(out)


def vbyte_decode(data: bytes) -> List[int]:
    """Decodes a contiguous VByte byte string back into a list of integers."""
    numbers = []
    current_num = 0
    shift = 0
    
    for byte in data:
        if byte & 0x80:  # Terminal byte
            current_num |= (byte & 0x7F) << shift
            numbers.append(current_num)
            current_num = 0
            shift = 0
        else:
            current_num |= (byte & 0x7F) << shift
            shift += 7
            
    return numbers


def delta_encode(sorted_ids: List[int]) -> List[int]:
    """
    Computes differences (gaps) between consecutive sorted document IDs.
    Example: [10, 15, 23, 24] -> [10, 5, 8, 1]
    """
    if not sorted_ids:
        return []
    deltas = [sorted_ids[0]]
    for i in range(1, len(sorted_ids)):
        deltas.append(sorted_ids[i] - sorted_ids[i - 1])
    return deltas


def delta_decode(deltas: List[int]) -> List[int]:
    """
    Reconstructs original sorted document IDs from delta gaps via prefix sum.
    Example: [10, 5, 8, 1] -> [10, 15, 23, 24]
    """
    if not deltas:
        return []
    result = [deltas[0]]
    for i in range(1, len(deltas)):
        result.append(result[-1] + deltas[i])
    return result


def compress_postings(doc_ids: List[int], term_freqs: List[int]) -> bytes:
    """
    Compresses a posting list:
    1. Delta-encodes sorted doc_ids.
    2. VByte-encodes deltas.
    3. VByte-encodes term frequencies.
    Format:
        len_delta_bytes (u32 LE, 4B)
        vbyte_deltas
        vbyte_tfs
    """
    import struct
    deltas = delta_encode(doc_ids)
    delta_bytes = vbyte_encode(deltas)
    tf_bytes = vbyte_encode(term_freqs)
    
    header = struct.pack("<I", len(delta_bytes))
    return header + delta_bytes + tf_bytes


def decompress_postings(compressed_data: bytes) -> Tuple[List[int], List[int]]:
    """
    Decompresses posting list into (doc_ids, term_freqs).
    """
    import struct
    len_delta_bytes = struct.unpack_from("<I", compressed_data, 0)[0]
    
    delta_slice = compressed_data[4 : 4 + len_delta_bytes]
    tf_slice = compressed_data[4 + len_delta_bytes :]
    
    deltas = vbyte_decode(delta_slice)
    doc_ids = delta_decode(deltas)
    tfs = vbyte_decode(tf_slice)
    
    return doc_ids, tfs
