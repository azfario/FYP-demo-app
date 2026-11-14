"""Fast-SCNN A6 inference architecture from the evaluated research source."""
import torch
from torch import nn
from torch.nn import functional as F


class ConvBNReLU(nn.Module):
    def __init__(self, in_ch, out_ch, ks=3, stride=1, padding=1, groups=1):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, ks, stride, padding, bias=False, groups=groups),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class DSConv(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, in_ch, 3, stride, 1, groups=in_ch, bias=False),
            nn.BatchNorm2d(in_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_ch, out_ch, 1, 1, 0, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class LinearBottleneck(nn.Module):
    def __init__(self, in_ch, out_ch, stride, t=6):
        super().__init__()
        hidden_ch = in_ch * t
        self.use_res = (stride == 1 and in_ch == out_ch)

        self.block = nn.Sequential(
            nn.Conv2d(in_ch, hidden_ch, 1, bias=False),
            nn.BatchNorm2d(hidden_ch),
            nn.ReLU(inplace=True),

            nn.Conv2d(hidden_ch, hidden_ch, 3, stride, 1, groups=hidden_ch, bias=False),
            nn.BatchNorm2d(hidden_ch),
            nn.ReLU(inplace=True),

            nn.Conv2d(hidden_ch, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch),
        )

    def forward(self, x):
        out = self.block(x)
        if self.use_res:
            out = out + x
        return out


class PyramidPooling(nn.Module):
    def __init__(self, in_ch, out_ch, pool_sizes=(1, 2, 3, 6)):
        super().__init__()
        inter_ch = in_ch // 4
        self.paths = nn.ModuleList()
        for ps in pool_sizes:
            self.paths.append(
                nn.Sequential(
                    nn.AdaptiveAvgPool2d(ps),
                    ConvBNReLU(in_ch, inter_ch, ks=1, stride=1, padding=0),
                )
            )
        self.out = ConvBNReLU(in_ch + len(pool_sizes) * inter_ch, out_ch, ks=3, stride=1, padding=1)

    def forward(self, x):
        h, w = x.shape[2:]
        feats = [x]
        for path in self.paths:
            y = path(x)
            y = F.interpolate(y, size=(h, w), mode="bilinear", align_corners=False)
            feats.append(y)
        x = torch.cat(feats, dim=1)
        return self.out(x)


class LearningToDownsample(nn.Module):
    def __init__(self, in_ch, dw_channels=(32, 48, 64)):
        super().__init__()
        self.conv = ConvBNReLU(in_ch, dw_channels[0], ks=3, stride=2, padding=1)
        self.dsconv1 = DSConv(dw_channels[0], dw_channels[1], stride=2)
        self.dsconv2 = DSConv(dw_channels[1], dw_channels[2], stride=2)

    def forward(self, x):
        x = self.conv(x)
        x = self.dsconv1(x)
        x = self.dsconv2(x)
        return x


class GlobalFeatureExtractor(nn.Module):
    def __init__(self, in_ch, block_channels=(64, 96, 128), num_blocks=(3, 3, 3), t=6):
        super().__init__()
        self.bottleneck1 = self._make_layer(in_ch, block_channels[0], num_blocks[0], stride=2, t=t)
        self.bottleneck2 = self._make_layer(block_channels[0], block_channels[1], num_blocks[1], stride=2, t=t)
        self.bottleneck3 = self._make_layer(block_channels[1], block_channels[2], num_blocks[2], stride=1, t=t)
        self.ppm = PyramidPooling(block_channels[2], block_channels[2])

    def _make_layer(self, in_ch, out_ch, blocks, stride, t):
        layers = [LinearBottleneck(in_ch, out_ch, stride=stride, t=t)]
        for _ in range(1, blocks):
            layers.append(LinearBottleneck(out_ch, out_ch, stride=1, t=t))
        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.bottleneck1(x)
        x = self.bottleneck2(x)
        x = self.bottleneck3(x)
        x = self.ppm(x)
        return x


class FeatureFusionModule(nn.Module):
    def __init__(self, high_ch, low_ch, out_ch):
        super().__init__()
        self.dwconv = nn.Sequential(
            nn.Conv2d(high_ch, out_ch, 3, 1, 1, groups=out_ch, bias=False),
            nn.BatchNorm2d(out_ch),
        )
        self.conv_low = nn.Sequential(
            nn.Conv2d(low_ch, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch),
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, high_res, low_res):
        low_res = F.interpolate(low_res, size=high_res.shape[2:], mode="bilinear", align_corners=False)
        low_res = self.dwconv(low_res)
        high_res = self.conv_low(high_res)
        out = high_res + low_res
        return self.relu(out)


class Classifier(nn.Module):
    def __init__(self, in_ch, num_classes):
        super().__init__()
        self.dsconv1 = DSConv(in_ch, in_ch, stride=1)
        self.dsconv2 = DSConv(in_ch, in_ch, stride=1)
        self.dropout = nn.Dropout(0.1)
        self.conv = nn.Conv2d(in_ch, num_classes, kernel_size=1)

    def forward(self, x):
        x = self.dsconv1(x)
        x = self.dsconv2(x)
        x = self.dropout(x)
        x = self.conv(x)
        return x


class FastSCNNFlood(nn.Module):
    def __init__(self, in_channels=15, num_classes=1):
        super().__init__()
        self.learning_to_downsample = LearningToDownsample(in_channels, dw_channels=(32, 48, 64))
        self.global_feature_extractor = GlobalFeatureExtractor(
            64, block_channels=(64, 96, 128), num_blocks=(3, 3, 3), t=6
        )
        self.feature_fusion = FeatureFusionModule(high_ch=128, low_ch=64, out_ch=128)
        self.classifier = Classifier(128, num_classes)

    def forward(self, x):
        size = x.shape[2:]
        high = self.learning_to_downsample(x)
        low = self.global_feature_extractor(high)
        fused = self.feature_fusion(high, low)
        out = self.classifier(fused)
        out = F.interpolate(out, size=size, mode="bilinear", align_corners=False)
        return out


class FastSCNNDetailRefinement(FastSCNNFlood):
    def __init__(self, in_channels=15, num_classes=1):
        super().__init__(in_channels=in_channels, num_classes=num_classes)
        self.detail_projection = ConvBNReLU(48, 32, ks=1, padding=0)
        self.context_projection = ConvBNReLU(128, 48, ks=1, padding=0)
        self.refine = nn.Sequential(DSConv(80, 64), DSConv(64, 32))
        self.correction = nn.Conv2d(32, num_classes, 1)
        nn.init.zeros_(self.correction.weight)
        nn.init.zeros_(self.correction.bias)

    def forward(self, x):
        size = x.shape[2:]
        detail = self.learning_to_downsample.conv(x)
        detail = self.learning_to_downsample.dsconv1(detail)
        high = self.learning_to_downsample.dsconv2(detail)
        low = self.global_feature_extractor(high)
        fused = self.feature_fusion(high, low)
        baseline = F.interpolate(self.classifier(fused), size=size, mode='bilinear', align_corners=False)
        projected = self.detail_projection(detail)
        context = F.interpolate(self.context_projection(fused), size=detail.shape[2:], mode='bilinear', align_corners=False)
        correction = self.correction(self.refine(torch.cat([projected, context], dim=1)))
        return baseline + F.interpolate(correction, size=size, mode='bilinear', align_corners=False)
