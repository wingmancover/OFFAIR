#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "OffairScriptTestLibrary.generated.h"

// PIE-only fixture creation for the Python integration driver.
UCLASS()
class OFFAIR_API UOffairScriptTestLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "OFFAIR|Tests",
        meta = (WorldContext = "WorldContextObject", DevelopmentOnly, BlueprintInternalUseOnly = "true"))
    static AActor* SpawnTestActor(const UObject* WorldContextObject, TSubclassOf<AActor> ActorClass);
};
