// Regional identities shared by the launcher and the emulator entry point.
// The HeartGold ES FIX file has a foreign header code. Its verified fingerprint
// opts into the Spanish layout; an unrelated French ROM must not.
#pragma once
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
extern "C" {
#include "sha1/sha1.h"
}

namespace RomVersions
{
inline bool Hgss(const std::string& code)
{
    return code == "IPGE" || code == "IPKE" || code == "IPGS" || code == "IPKF";
}

inline const char* RequiredHash(const std::string& code)
{
    if (code == "IPKF") return "09fb5438647a28ef680234777c73ccc6cbe63cf4";
    return nullptr;
}

inline bool DigestMatches(SHA1_CTX& context, const char* expected)
{
    unsigned char digest[20];
    SHA1Final(digest, &context);
    char hex[41];
    for (int i = 0; i < 20; i++) std::snprintf(hex + i * 2, 3, "%02x", digest[i]);
    return !std::strcmp(hex, expected);
}

inline bool Accept(const std::string& code, const std::vector<unsigned char>& rom)
{
    const char* expected = RequiredHash(code);
    if (!expected) return true;
    SHA1_CTX context;
    SHA1Init(&context);
    SHA1Update(&context, rom.data(), (uint32_t)rom.size());
    return DigestMatches(context, expected);
}

inline bool AcceptFile(const std::string& code, const std::string& path)
{
    const char* expected = RequiredHash(code);
    if (!expected) return true;
    FILE* file = std::fopen(path.c_str(), "rb");
    if (!file) return false;
    SHA1_CTX context;
    SHA1Init(&context);
    unsigned char buffer[65536];
    size_t size;
    while ((size = std::fread(buffer, 1, sizeof buffer, file)) != 0)
        SHA1Update(&context, buffer, (uint32_t)size);
    const bool ok = !std::ferror(file);
    std::fclose(file);
    return ok && DigestMatches(context, expected);
}
}
