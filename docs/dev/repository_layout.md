# ScyllaDB repository layout


This document is meant to provide a helicopter view over the ScyllaDB repository.

It’d make us very happy if this document will achieve the following objectives:
* shorten the ramp up time of an onboarding core engineer
* improve code search locality during development of the first few tasks
* map the theoretical knowledge one acquires during the first few days to actual source files on disk
* get a better chance of understanding the project top-down

Please note the source code is in an ever changing state with continuous effort being put in to refactor, decouple, isolate components. The source code hierarchy still looks flat with many source files located in the root directory, so some of these files might move in the future, some component dirs might get split, moved or removed altogether, we’ll do our best to keep the doc accurate.

`alternator/`

This is the location of the Alternator project which provides interoperability with Amazon DynamoDB, here’s a Scylla Univerisity [course](https://university.scylladb.com/courses/scylla-alternator/) on it. 

`abseil/`

Bundled abseil library

`api/`

This location contains source files managing Scylla REST APIs. ScyllaDB is being managed using the APIs defined here, the nodetool utility for instance uses such APIs to expose operations. The precursor of these APIs was Cassandra’s JMX.

`auth/`

Everything related to authorization and authentication between the clients and Scylla nodes.

`bin/`

Scripts/symlinks like nodetool, cqlsh. 

`cdc/`

Location for the [Change Data Capture](
https://opensource.docs.scylladb.com/stable/features/cdc/) feature which offers mechanism
for looking at the history of updates to tables.

`cmake/`

This location contains all the build files related to cmake. At this moment there is an ongoing effort to migrate from configure.py based build to cmake based builds.

`compaction/`

Everything related to ScyllaDB compaction. There are files defining the supported compaction strategies, the compaction_manager deciding when compaction is triggered and some other infrastructure code.

`conf/`

This directory contains configuration files used as defaults for running ScyllaDB locally.

`cql3/`

That’s the location of the Cassandra based fronteded. This location contains the grammar defining CQL, the parser, extensions, etc.

`data_dictionary/`

In Scylla, nodes are coordinators or replica. data_dictionary is an abstraction on top of them so that you don’t have to use monster classes like replica database directly.


`db/`

This is a mixed bag of multiple components. There is replica code, there is snapshot code, commit log code, etc. The db/view subdirectory contains code for replicating from a base table into a view.

`debug/`

Assistance code for tracing/debugging (potentially unused/broken?).
 
`dht/`

Distributed HashTable. This is where most of the logic for partitioning lives and where things like the hash algorithm for obtaining the token can be found.

`direct_failure_detector/`

This component is responsible for detecting whether a node is reachable or not, it keeps some sort of heartbeat channel open with a node to see when it goes down.

`exceptions/`

This is a place that gathers all exception types related mostly to csql3, but others too.

`gms/`

The Gossip protocol implementation used for distributing information between nodes within a Scylla cluster. Whenever you want to make a piece of information available to everyone in the cluster, you put it on gossip and eventually everybody will get to know it.
Rumour has it that the protocol is not as reliable as we’d want it to be, so it might get replaced sometime in the future.

`idl/`

Interface definition language, it’s used for defining the message body of inter-node communication within the cluster. It’s very flexible as it allows extensions of the message bodies without breaking compatibility. The idl-compiler.py does the code generation based on specification.

`index/`

This location defines the secondary_index class, closely related to the materialized views concept in ScyllaDB, see this [link](https://docs.datastax.com/en/cassandra-oss/3.0/cassandra/dml/dmlIndexInternals.html) for an explanation on how that works.

`lang/`

Experimental feature for supporting UDFs. There’re Lua and Wasm files implementing that support.

`licenses/`

Licenses for ScyllaDB and bundled packages.

`locator/`

This is the location for most of the code related to replication, replication strategies, RF, CL.
This is where the new tablets feature are implemented as well, find a description of them in this [link](https://opensource.docs.scylladb.com/stable/architecture/tablets.html). Basically they allow faster and more efficient scaling of the ScyllaDB clusters.


`message/`

This is the layer of communication between Scylla nodes. It is highly related to `idl/`, it defines high-level methods for serialization/deserialization for writing RPCs.

`mutation/`

This is where the code belonging to the datamodel lives. Any write operation is a mutation and a mutation is basically a diff. Mutations can be combined out of order because cells are timestamped.

`mutation_writer/`

Code related to mutations, but more on the front on how to split mutations, how to make data from a mutation before a timestamp to fit in a particular bucket and also how to distribute mutation on shards.

`node_ops/`

Support code for operations that change the topology of a ScyllaDB cluster.

`repair/`

Implementation for the node repair process. As write operations are eventual consistent, sometimes node might fall out of sync, especially when new nodes join the cluster. Node repair is a process scheduled to run in the background which goes over all the nodes and make sure their data is in sync.
The old way of doing this is via the streaming processes, but that was slower and had the drawback of not being resumable in case of failure.
More on this topic [here](https://www.scylladb.com/2023/12/07/faster-safer-node-operations-with-repair-vs-streaming/),

`raft/`

Implementation for the Raft distributed state machine. This is planned to be the replacement for the Gossip protocol and will help store the topology, schema, metadata, etc. Raft has formal proofs for correctness or, as @denesb likes to say, Gossip is like “trust me bro!” compared to a lawyer-drafted contract from Raft.

`readers/`

ScyllaDB library for readers. There is a reader interface defined and implementations for SSTable readers, Memtable readers, network readers, etc
All of these readers can be combined to produce a common output stream.

`redis/`

Redis driver connector contributed by external contributor.

`reloc/`

Code related to packaging ScyllaDB as rpm, deb, etc. This is called reloc because ScyllaDB is packaged as a relocatable package with all dependencies bundled in.

`replica/`

Most of the code related to replica lives here. As modularization work evolves, even more replica code will be moved here. Giants like the database and table classes live here.

`rust/`

Code related to UDFs, closely related to lang/

`schema/`

This location contains code related to schema and metadata.

`scripts/`

Development and maintenance scripts, most notably being open-coredump.sh, a convenience script for obtaining a debugging environment with frozen toolchain.

`seastar/`

A git submodule for the [Seastar](https://github.com/scylladb/seastar) library repository.
This library deserves a separate subdocument to describe its layout.

`service/`

Coordinator node code. There is also code using Raft for consistent topology changes, consistent schema changes, etc.

`sstables/`

This is where the code for reading and writing for on-disk SSTables lives.

`streaming/`

This location contains the implementation for the streaming algorithm used to provision and sync nodes. To be replaced by the algorithm defined in repair/ as described above.

`swagger-ui/`

This is closely related to api/

`tasks/`

Task manager implementation for the internal background tasks in Scylla.

`test/`

All tests of ScyllaDB live under this path. The test.py script is used to run those tests, although there is an ongoing effort to move away from this script to pytest.
test/perf contains the microbenchmarks we frequently ran to look for regressions.

`tools/`

Various user tools like notedool, tools for inspecting the content of an SSTable or dumping an SSTable to JSON.

`tracing/`

Diagnosis capabilities integrated in CQL.

`transport/`

This is the networking layer implementation for the csql3 clients, it defines the packets, format, etc.

`types/`

The type system of Scylla, Alternator, etc. All data types, casting operations are defined here.

`unified/`

Packaging utilities, install/uninstall scripts.

`utils/`

A mixed bag of everything. In-house containers, allocation strategies, utility function implementations, etc.

