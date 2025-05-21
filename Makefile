DEBUG := true
BRANCH := adelynnmckay

.PHONY: debug
debug:
	chmod +x god.sh && \
	DEBUG=$(DEBUG) BRANCH=$(BRANCH) ./god.sh
