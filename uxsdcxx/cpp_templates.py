from string import Template

# See https://www.obj-sys.com/docs/xbv23/CCppUsersGuide/ch04.html.
atomic_builtins = {
	"string": "const char *",
	"boolean": "bool",
	"float": "float",
	"decimal": "int",
	"integer": "int",
	"nonPositiveInteger": "int",
	"negativeInteger": "int",
	"long": "long",
	"int": "int",
	"short": "short",
	"byte": "char",
	"nonNegativeInteger": "unsigned int",
	"unsignedLong": "unsigned long",
	"unsignedInt": "unsigned int",
	"unsignedShort": "unsigned short",
	"unsignedByte": "unsigned byte",
	"positiveInteger": "unsigned int",
	"double": "double",
	"IDREF": "const char *",
	"ID": "const char *",
}

atomic_builtin_load_formats = {
	"string": "char_pool.add(%s)",
	"boolean": "std::strtol(%s, NULL, 10)",
	"float": "std::strtof(%s, NULL)",
	"decimal": "std::strtol(%s, NULL, 10)",
	"integer": "std::strtol(%s, NULL, 10)",
	"nonPositiveInteger": "std::strtol(%s, NULL, 10)",
	"negativeInteger": "std::strtol(%s, NULL, 10)",
	"long": "std::strtoll(%s, NULL, 10)",
	"int": "std::strtol(%s, NULL, 10)",
	"short": "std::strtol(%s, NULL, 10)",
	"byte": "std::strtol(%s, NULL, 10)",
	"nonNegativeInteger": "std::strtoul(%s, NULL, 10)",
	"unsignedLong": "std::strtoull(%s, NULL, 10)",
	"unsignedInt": "std::strtoul(%s, NULL, 10)",
	"unsignedShort": "std::strtoul(%s, NULL, 10)",
	"unsignedByte": "std::strtoul(%s, NULL, 10)",
	"positiveInteger": "std::strtoul(%s, NULL, 10)",
	"double": "std::strtod(%s, NULL)",
	"IDREF": "char_pool.add(%s)",
	"ID": "char_pool.add(%s)",
}

cpp_keywords = ["alignas", "alignof", "and", "and_eq", "asm", "atomic_cancel", "atomic_commit", "atomic_noexcept",
			"auto", "bitand", "bitor", "bool", "break", "case", "catch", "char", "char8_t", "char16_t", "char32_t", "class",
			"compl", "concept", "const", "consteval", "constexpr", "const_cast", "continue", "co_await", "co_return",
			"co_yield", "decltype", "default", "delete", "do", "double", "dynamic_cast", "else", "enum", "explicit",
			"export", "extern", "false", "float", "for", "friend", "goto", "if", "inline", "int", "long", "mutable",
			"namespace", "new", "noexcept", "not", "not_eq", "nullptr", "operator", "or", "or_eq", "private",
			"protected", "public", "reflexpr", "register", "reinterpret_cast", "requires", "return", "short", "signed",
			"sizeof", "static", "static_assert", "static_cast", "struct", "switch", "synchronized", "template", "this",
			"thread_local", "throw", "true", "try", "typedef", "typeid", "typename", "union", "unsigned", "using",
			"virtual", "void", "volatile", "wchar_t", "while", "xor", "xor_eq"]

header_comment = Template("""/*
 * This file is generated by uxsdcxx $version.
 * https://github.com/duck2/uxsdcxx
 * Modify only if your build process doesn't involve regenerating this file.
 *
 * Cmdline: $cmdline
 * Input file: $input_file
 * md5sum of input file: $md5
 */
""")

includes = """
#include <bitset>
#include <cassert>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include <error.h>
#include <stddef.h>
#include <stdint.h>
#include "pugixml.hpp"
"""

collapsed_vec_defn = """
/**
 * Stores a vector of elements in a shared pool. Consists
 * of an offset into the pool and a size. It's faster than a regular
 * vector, but one can only insert into it when it's the last vector
 * in the pool.
 */
template<class T, std::vector<T> &pool>
class collapsed_vec {
private:
	uint32_t _size;
	uint32_t _offset;
public:
	inline collapsed_vec(){
		_size = 0;
		_offset = pool.size();
	}
	inline T& back(){
		return pool[_offset+_size-1];
	}
	inline T* begin(){
		return &pool[_offset];
	}
	inline T* end(){
		return &pool[_offset+_size];
	}
	inline T& operator[](uint32_t i){
		return pool[_offset+i];
	}
	inline void push_back(const T &x){
		assert(_size+_offset == pool.size());
		pool.push_back(x);
		_size++;
	}
	inline uint32_t size(){
		return _size;
	}
};
"""

char_pool_defn = """
/**
 * A pool for string data. It manages memory in a vector of chunks
 * with used and size information. The chunk sizes increase exponentially
 * with every new chunk.
 */
class char_pool_impl {
private:
	const uint32_t INITIAL_SIZE = 1024;
	struct chunk {
		uint32_t used;
		uint32_t size;
		char * mem;
	};
	std::vector<chunk> chunks;
public:
	inline char_pool_impl(){
		chunk c;
		c.used = 0;
		c.size = INITIAL_SIZE;
		c.mem = (char *)std::malloc(INITIAL_SIZE);
		chunks.emplace_back(c);
	}
	inline ~char_pool_impl(){
		for(auto &c: chunks)
			free(c.mem);
	}
	/**
	 * Copies x into the string pool and returns a pointer to it.
	 * If x is not small enough to fit in any chunk, a new chunk is
	 * allocated with the size of max(len(x), last chunk's size*2).
	 */
	inline const char *add(const char *x){
		uint32_t len = std::strlen(x)+1;
		char *out;
		for(auto &c: chunks){
			if(c.used+len <= c.size){
				out = &c.mem[c.used];
				c.used += len;
				std::memcpy(out, x, len);
				return out;
			}
		}
		chunk n;
		n.used = len;
		n.size = std::max(chunks.back().size*2, len);
		n.mem = (char *)std::malloc(n.size);
		std::memcpy(n.mem, x, len);
		chunks.emplace_back(n);
		return n.mem;
	}
	/**
	 * Frees all chunks except the first one and leaves the pool
	 * in a usable state.
	 */
	inline void clear(){
		for(uint32_t i=1; i<chunks.size(); i++){
			free(chunks[i].mem);
		}
		chunks.resize(1);
		chunks[0].used = 0;
		std::memset(chunks[0].mem, 0, INITIAL_SIZE);
	}
};
"""

dfa_error_decl = """
/**
 * Internal error function for xs:choice and xs:sequence validators.
 */
void dfa_error(const char *wrong, int *states, const char **lookup, int len);
"""

all_error_decl = """
/**
 * Internal error function for xs:all validators.
 */
template<std::size_t N>
void all_error(std::bitset<N> gstate, const char **lookup);
"""

attr_error_decl = """
/**
 * Internal error function for attribute validators.
 */
template<std::size_t N>
void attr_error(std::bitset<N> astate, const char **lookup);
"""

dfa_error_defn = """
void dfa_error(const char *wrong, int *states, const char **lookup, int len){
	std::vector<std::string> expected;
	for(int i=0; i<len; i++){
		if(states[i] != -1) expected.push_back(lookup[i]);
	}

	std::string expected_or = expected[0];
	for(unsigned int i=1; i<expected.size(); i++)
		expected_or += std::string(" or ") + expected[i];

	throw std::runtime_error("Expected " + expected_or + ", found " + std::string(wrong));
}
"""

all_error_defn = """
template<std::size_t N>
void all_error(std::bitset<N> gstate, const char **lookup){
	std::vector<std::string> missing;
	for(unsigned int i=0; i<N; i++){
		if(gstate[i] == 0) missing.push_back(lookup[i]);
	}

	std::string missing_and = missing[0];
	for(unsigned int i=1; i<missing.size(); i++)
		missing_and += std::string(", ") + missing[i];

	throw std::runtime_error("Didn't find required elements " + missing_and + ".");
}
"""

attr_error_defn = """
template<std::size_t N>
void attr_error(std::bitset<N> astate, const char **lookup){
	std::vector<std::string> missing;
	for(unsigned int i=0; i<N; i++){
		if(astate[i] == 0) missing.push_back(lookup[i]);
	}

	std::string missing_and = missing[0];
	for(unsigned int i=1; i<missing.size(); i++)
		missing_and += std::string(", ") + missing[i];

	throw std::runtime_error("Didn't find required attributes " + missing_and + ".");
}
"""
