
/*
 * Copyright (C) 2015-present ScyllaDB
 */

/*
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

#pragma once

#include <map>
#include <vector>
#include <seastar/core/sstring.hh>

#include "seastarx.hh"
#include "locator/tablets.hh"

namespace cql_transport {
namespace messages {

class result_message {
    std::vector<sstring> _warnings;
    std::map<sstring, bytes> _custom_payload;
public:
    class visitor;
    class visitor_base;

    virtual ~result_message() {}

    virtual void accept(visitor&) const = 0;

    void add_warning(sstring w) {
        _warnings.push_back(std::move(w));
    }

    const std::vector<sstring>& warnings() const {
        return _warnings;
    }

    void add_custom_payload(sstring key, bytes value) {
        _custom_payload[key] = value;
    }

    void add_tablet_info(locator::tablet_replica_set tablet_replicas, dht::token_range token_range) {
        if (!tablet_replicas.empty()) {
            auto replicas_bytes = bytes();
            replicas_bytes.append(reinterpret_cast<const int8_t*>(std::to_string(tablet_replicas.size()).data()), sizeof(tablet_replicas.size()));
            for (auto replica : tablet_replicas) {
                replicas_bytes.append(reinterpret_cast<const int8_t*>(replica.host.to_sstring().data()), replica.host.to_sstring().size());
                replicas_bytes.append(reinterpret_cast<const int8_t*>(std::to_string(replica.shard).data()), sizeof(replica.shard));
            }
            this->add_custom_payload("tablet_replicas", replicas_bytes);
            auto token_bytes = bytes();
            auto first_token = token_range.start()->value();
            auto last_token = token_range.end()->value();
            token_bytes.append(first_token.data().data(), first_token.data().size());
            token_bytes.append(last_token.data().data(), last_token.data().size());
            this->add_custom_payload("token_range", token_bytes);
        }
    }

    const std::map<sstring, bytes>& custom_payload() const {
        return _custom_payload;
    }

    virtual std::optional<unsigned> move_to_shard() const {
        return std::nullopt;
    }

    virtual bool is_exception() const {
        return false;
    }

    virtual void throw_if_exception() const {}
    //
    // Message types:
    //
    class void_message;
    class set_keyspace;
    class prepared;
    class schema_change;
    class rows;
    class bounce_to_shard;
    class exception;
};

std::ostream& operator<<(std::ostream& os, const result_message& msg);

}
}
